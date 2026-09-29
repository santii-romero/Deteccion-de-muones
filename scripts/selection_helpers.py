"""Pure selection/weighting helpers retained for regression checks; no historical I/O."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import numpy as np
from muones.background import secondary_groups
LO,HI=.12,1.4

def regroup(pulses, t0):
    index = {str(p['pulse_id']): p for p in pulses}
    output = []
    for g in secondary_groups(pulses, t0):
        pp = [index[k] for k in g['pulse_ids'].split(';')]
        target = [p for p in pp if int(p['channel']) in (2, 3)]
        good = [p for p in target if p['status'] == 'accepted']
        eligible = bool(target) and len(good) == len(target)
        timing = good or target
        output.append({**g, 'original_delay_ns': g['delay_ns'],
            'delay_ns': float(np.mean([p['time_ns'] for p in timing]) - t0) if timing else g['delay_ns'],
            'eligible_without_ch1_veto': eligible,
            'has_clean_target': bool(good),
            'score_mV': max((float(p['amplitude_mV']) for p in target), default=0.),
            'target_quality_flags': ';'.join(sorted({f for p in target for f in p['reasons'].split(';') if f})),
            'target_channels': '+'.join(map(str, sorted({int(p['channel']) for p in target})))})
    return output

def chosen_group(groups):
    eligible = [g for g in groups if g['side'] == 1 and g['eligible_without_ch1_veto']]
    original = [g for g in eligible if g['selected']]
    # Preserve original clean assignment whenever present, before window cut.
    pool = original or eligible
    return max(pool, key=lambda g: (g['score_mV'], -g['delay_ns'])) if pool else None

def allowed(event, group, pulses, level):
    if level == 0:
        return group['status'] == 'candidate'
    if level < 6 and event['count_status'] != 'accepted':
        return False
    if level == 5 and event['decay_status'] not in ('candidate', 'ambiguous'):
        return False
    channel23 = [p for p in pulses if int(p['channel']) in (2, 3)]
    if level >= 7:
        return bool(pulses)  # The user's broad definition does not specify a secondary channel.
    if not channel23:
        return False
    if level >= 5:
        return True  # Explicit maximum-inclusion stress test, including hard pulse flags.
    reasons = set(filter(None, group['reasons'].split(';')))
    accepted_reasons = {'compatible_topology_backgrounds_unmeasured', 'prompt3_present_control_sample'}
    if level >= 2:
        accepted_reasons.add('prompt3_uncertain')
    if level >= 3:
        accepted_reasons.add('late_ch1_accidental_or_direction_ambiguous')
    if level >= 4:
        accepted_reasons.update(('secondary_quality_uncertain', 'no_clean_secondary_ch2_or_ch3'))
    if not reasons.issubset(accepted_reasons):
        return False
    if level < 4:
        return group['status'] != 'excluded' and all(p['status'] == 'accepted' for p in channel23)
    return any(p['status'] != 'excluded' for p in channel23)

def choose(options, rule):
    """Select on the full search region, not only the eventual fit window."""
    if rule == 'earliest':
        return min(options, key=lambda x: (float(x['delay_ns']), int(x['group_id'])))
    return max(options, key=lambda x: (float(x['peak_amplitude_ch23_mV']), -float(x['delay_ns'])))

def make_data(rows, run):
    return dict(run=run, t=np.array([float(r['delay_ns']) / 1000 for r in rows]),
                lo=LO, hi=HI, off=0, alpha=0., pure_signal=True)

def mean_offset(beta, width):
    """Stable expected delay minus the lower bound, including beta=0."""
    beta = np.asarray(beta, dtype=float)
    out = np.array(width / 2 - beta * width**2 / 12 + beta**3 * width**4 / 720)
    mask = np.abs(beta * width) >= 1e-3
    np.divide(1., beta, out=out, where=mask)
    term = np.zeros_like(beta)
    np.divide(width, np.expm1(beta * width), out=term, where=mask)
    return np.where(mask, out - term, out)

def beta_from_mean(means, width):
    """MLE from the sufficient statistic; independent check of fit()."""
    means = np.asarray(means, dtype=float)
    lower = np.zeros_like(means)
    upper = np.full_like(means, 100.)
    for _ in range(55):
        mid = (lower + upper) / 2
        move_lower = mean_offset(mid, width) > means
        lower = np.where(move_lower, mid, lower)
        upper = np.where(move_lower, upper, mid)
    return np.where(means >= width / 2, 0., (lower + upper) / 2)
