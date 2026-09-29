"""Transparent pulse and event selection on un-smoothed, baseline-subtracted data.

No particle identity, detector efficiency, direction of flight or lifetime is inferred.
Thresholds are fixed before evaluating the held-out split. All failures keep reasons.
"""
import hashlib
import numpy as np
from scipy.signal import find_peaks


def split(uid):
    return 'evaluation' if int(hashlib.sha256(uid.encode()).hexdigest()[:8], 16) % 5 == 0 else 'development'


def robust_stats(v, floor=0.1):
    base = float(np.median(v))
    noise = max(floor, float(1.4826 * np.median(np.abs(v-base))))
    return base, noise


def half_width(t, y, i):
    half = y[i]/2
    lo = hi = i
    while lo > 0 and y[lo-1] > half:
        lo -= 1
    while hi < len(y)-1 and y[hi+1] > half:
        hi += 1
    left = t[lo] if lo == 0 else float(np.interp(half, [y[lo-1], y[lo]], [t[lo-1], t[lo]]))
    right = t[hi] if hi == len(y)-1 else float(np.interp(half, [y[hi+1], y[hi]], [t[hi+1], t[hi]]))
    return right-left, hi-lo+1, lo, hi


def analyze_channel(t, v, channel, cfg):
    exc = cfg['baseline_exclude_ns']
    mask = (t < exc[0]) | (t > exc[1])
    if mask.sum() < 20:
        mask = np.ones(len(t), dtype=bool)
    base, noise = robust_stats(v[mask], cfg['noise_floor_mV'])
    # Clip candidate pulses for the baseline only; waveform samples remain unchanged.
    trimmed = mask & (np.abs(v-base) < 3.5*noise)
    if trimmed.sum() >= 20:
        base, noise = robust_stats(v[trimmed], cfg['noise_floor_mV'])
    y = base-v
    dt = float(np.median(np.diff(t)))
    threshold = max(cfg['amplitude_mV'], cfg['amplitude_sigma']*noise)
    seed_height = max(cfg['seed_amplitude_mV'], cfg['seed_sigma']*noise)
    prom = max(cfg['seed_prominence_mV'], cfg['seed_prominence_sigma']*noise)
    idx, props = find_peaks(y, height=seed_height, prominence=prom,
                           distance=max(1, int(np.ceil(cfg['peak_distance_ns']/dt))))
    positive_threshold = max(cfg['positive_mV'], cfg['positive_sigma']*noise)
    positives, _ = find_peaks(-y, height=positive_threshold, prominence=prom,
                             distance=max(1, int(np.ceil(cfg['peak_distance_ns']/dt))))
    baseline_rail = float(np.mean(np.abs(v[mask]) >= cfg['rail_mV']))
    ch_flags = []
    if noise > cfg['max_noise_mV']:
        ch_flags.append('excess_noise')
    if baseline_rail > cfg['max_baseline_rail_fraction']:
        ch_flags.append('baseline_clipping')
    metrics = dict(channel=channel, baseline_mV=base, noise_mV=noise, threshold_mV=threshold,
                   baseline_rail_fraction=baseline_rail, flags=';'.join(ch_flags),
                   positive_max_mV=float((-y).max()), negative_max_mV=float(y.max()))
    pulses = []
    for k, i in enumerate(idx):
        ti, amp = float(t[i]), float(y[i])
        width, support, lo, hi = half_width(t, y, i)
        local = np.abs(t-ti) <= cfg['local_radius_ns']
        core = (t >= t[lo]-dt) & (t <= t[hi]+dt)
        # Local baseline uses flanks only; a real secondary is not subtracted away.
        flank = (np.abs(t-ti) >= 35) & (np.abs(t-ti) <= 100) & (np.abs(y) < 3.5*noise)
        drift = float(np.median(v[flank])-base) if flank.sum() >= 12 else 0.0
        neg_near = int(np.sum(np.abs(t[idx]-ti) <= cfg['local_radius_ns']))
        pos_near = int(np.sum(np.abs(t[positives]-ti) <= cfg['local_radius_ns']))
        flags = list(ch_flags)
        if amp < threshold:
            flags.append('below_analysis_threshold')
        if width < cfg['width_min_ns'] or support < 2:
            flags.append('narrow_or_single_sample')
        if width > cfg['width_max_ns']:
            flags.append('broad_pulse')
        if ti-t[0] < cfg['edge_margin_ns'] or t[-1]-ti < cfg['edge_margin_ns']:
            flags.append('edge_truncated')
        if np.any(np.abs(v[core]) >= cfg['rail_mV']):
            flags.append('pulse_clipping')
        if abs(drift) > max(cfg['max_drift_mV'], 2*noise):
            flags.append('local_baseline_shift')
        if neg_near >= 3 and pos_near >= 2:
            flags.append('bipolar_oscillation')
        elif pos_near and np.max(-y[local]) > max(positive_threshold, .65*amp):
            flags.append('large_positive_lobe')
        hard = {'excess_noise','baseline_clipping','bipolar_oscillation','narrow_or_single_sample'}
        status = 'excluded' if hard.intersection(flags) else ('ambiguous' if flags else 'accepted')
        ar = (t >= ti-12) & (t <= ti+25)
        pulses.append(dict(channel=channel, sample=int(i), time_ns=ti, amplitude_mV=amp,
                           snr=amp/noise, prominence_mV=float(props['prominences'][k]),
                           width_ns=float(width), half_height_samples=int(support),
                           area_mV_ns=float(np.trapezoid(y[ar], t[ar])),
                           baseline_mV=base, noise_mV=noise, threshold_mV=threshold,
                           local_drift_mV=drift, nearby_negative_peaks=neg_near,
                           nearby_positive_peaks=pos_near, status=status, reasons=';'.join(flags)))
    return metrics, pulses


def group_pulses(pulses, tolerance):
    groups = []
    for p in sorted(pulses, key=lambda x: x['time_ns']):
        if groups and p['time_ns']-groups[-1][0]['time_ns'] <= tolerance:
            groups[-1].append(p)
        else:
            groups.append([p])
    return groups


def classify(event, cfg):
    """Return event metrics, every seed pulse, and every delayed group."""
    r = dict(uid=event.uid, source=event.source, run=event.run, file_index=event.file_index,
             ordinal=event.ordinal, event_id=event.event_id, timestamp=event.timestamp,
             line=event.line, byte_offset=event.byte_offset, byte_length=event.byte_length,
             split=split(event.uid), n_samples=len(event.data), count_status='excluded',
             count_reasons='', prompt3_status='not_evaluated', topology='unclassified',
             t0_ns='', max_delay_ns='', decay_status='not_evaluable', decay_reasons='',
             candidate_groups=0, ambiguous_groups=0, excluded_groups=0,
             efficiency_status='unavailable_acquisition_selected_ch2', lifetime_fit_status='not_validated')
    errors = list(event.errors)
    if len(event.data) not in cfg['expected_samples']:
        errors.append('unexpected_sample_count')
    if errors:
        r['count_reasons'] = ';'.join(errors)
        r['decay_reasons'] = 'invalid_record'
        return r, [], []
    t, waves = event.data[:,0], event.data[:,1:]
    metrics, pulses = [], []
    for ch in range(3):
        m, pp = analyze_channel(t, waves[:,ch], ch+1, cfg)
        metrics.append(m)
        r.update({f'ch{ch+1}_{key}': value for key,value in m.items() if key != 'channel'})
        pulses.extend(pp)
    for i,p in enumerate(pulses):
        p.update(uid=event.uid, pulse_id=i, run=event.run, event_id=event.event_id)
    a, b = cfg['prompt_search_ns']
    prompt = [p for p in pulses if a <= p['time_ns'] <= b]
    pairs = [(p,q) for p in prompt if p['channel']==1 for q in prompt if q['channel']==2
             if abs(p['time_ns']-q['time_ns']) <= cfg['coincidence_ns']]
    if not pairs:
        r['count_reasons'] = 'no_resolved_ch1_ch2_pair'
        r['decay_reasons'] = 'initial_coincidence_missing'
        return r, pulses, []
    rank = {'accepted':0,'ambiguous':1,'excluded':2}
    pairs.sort(key=lambda pair:(max(rank[pair[0]['status']],rank[pair[1]['status']]),pair[0]['time_ns']))
    p, q = pairs[0]
    t0 = p['time_ns']
    r['t0_ns'] = t0
    r['max_delay_ns'] = float(t[-1]-cfg['edge_margin_ns']-t0)
    reasons = sorted(set(filter(None, (p['reasons']+';'+q['reasons']).split(';'))))
    r['count_status'] = max((p['status'],q['status']), key=lambda s:rank[s])
    r['count_reasons'] = ';'.join(reasons) or 'resolved_negative_ch1_ch2_coincidence'
    ch3 = [x for x in pulses if x['channel']==3 and abs(x['time_ns']-t0)<=cfg['coincidence_ns']]
    r['prompt3_status'] = ('detected' if any(x['status']=='accepted' for x in ch3) else
                            'ambiguous' if ch3 or metrics[2]['flags'] else 'not_detected_above_threshold')
    r['topology'] = ('prompt_123' if r['prompt3_status']=='detected' else
                     'prompt_12_no_resolved_3' if r['prompt3_status']=='not_detected_above_threshold' else 'prompt_12_uncertain_3')
    delayed = [x for x in pulses if x['time_ns']-t0 >= cfg['min_delay_ns']]
    groups = []
    for j, group in enumerate(group_pulses(delayed,cfg['coincidence_ns'])):
        good = [x for x in group if x['status']=='accepted']
        channels = sorted(set(x['channel'] for x in good))
        all_channels = sorted(set(x['channel'] for x in group))
        rr = []
        status = 'candidate'
        if r['count_status'] != 'accepted':
            rr.append('initial_coincidence_'+r['count_status'])
        if not any(c in channels for c in [2,3]):
            rr.append('no_clean_secondary_ch2_or_ch3')
        if any(x['status']!='accepted' for x in group):
            rr.append('secondary_quality_uncertain')
        if 1 in all_channels:
            rr.append('late_ch1_accidental_or_direction_ambiguous')
        if r['prompt3_status']=='detected':
            rr.append('prompt3_present_control_sample')
        elif r['prompt3_status']=='ambiguous':
            rr.append('prompt3_uncertain')
        if rr:
            status = 'ambiguous'
        if r['count_status']=='excluded' or all(x['status']=='excluded' for x in group):
            status = 'excluded'
        delay = float(np.mean([x['time_ns'] for x in good or group])-t0)
        groups.append(dict(uid=event.uid, group_id=j, run=event.run, event_id=event.event_id,
                           split=r['split'], channels='+'.join(map(str,all_channels)),
                           clean_channels='+'.join(map(str,channels)), delay_ns=delay,
                           min_amplitude_mV=min(x['amplitude_mV'] for x in good or group),
                           status=status, reasons=';'.join(rr) or 'compatible_topology_backgrounds_unmeasured',
                           pulse_ids=';'.join(str(x['pulse_id']) for x in group)))
    for name in ['candidate','ambiguous','excluded']:
        r[name+'_groups'] = sum(g['status']==name for g in groups)
    if r['count_status']!='accepted':
        r['decay_status'] = 'not_evaluable'
        r['decay_reasons'] = 'initial_coincidence_'+r['count_status']
    elif r['candidate_groups']:
        r['decay_status'] = 'candidate'
        r['decay_reasons'] = 'compatible_secondary_identity_unconfirmed'
    elif r['ambiguous_groups']:
        r['decay_status'] = 'ambiguous'
        r['decay_reasons'] = 'review_delayed_group_reasons'
    elif groups:
        r['decay_status'] = 'excluded_secondary'
        r['decay_reasons'] = 'all_secondaries_fail_quality'
    else:
        r['decay_status'] = 'no_secondary_above_threshold'
        r['decay_reasons'] = 'absence_is_not_no_decay'
    return r, pulses, groups
