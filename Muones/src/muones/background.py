"""Symmetric accidental controls; unchanged v1 seed/quality decisions."""
import numpy as np
from .filters import group_pulses


def windows(row, cfg):
    t0 = float(row['t0_ns'])
    upper = float(row['max_delay_ns'])
    lo, hi = cfg['matched_lag_ns']
    hi = min(hi, t0-cfg['edge_ns'], upper)
    flo, fhi = cfg['fit_ns']
    return lo, max(lo, hi), flo, max(flo, min(fhi, upper))


def secondary_groups(pulses, t0, tolerance=15, guard=60):
    """Group each side separately. Positive side exactly reproduces v1.

    No reversal of asymmetric pulse waveforms or quality criteria is performed.
    Every group is retained with rejection reasons, including low-quality seeds.
    """
    out = []
    for side in [-1, 1]:
        seeds = [p for p in pulses if side*(p['time_ns']-t0) >= guard]
        for j, group in enumerate(group_pulses(seeds, tolerance)):
            good = [p for p in group if p['status'] == 'accepted']
            channels = sorted({int(p['channel']) for p in group})
            reasons = []
            if not any(int(p['channel']) in [2, 3] for p in good):
                reasons.append('no_clean_secondary_ch2_or_ch3')
            if len(good) != len(group):
                reasons.append('secondary_quality_uncertain')
            if 1 in channels:
                reasons.append('ch1_seed_veto')
            out.append(dict(side=side, group_id=j,
                delay_ns=float(np.mean([p['time_ns'] for p in good or group])-t0),
                channels='+'.join(map(str, channels)), selected=not reasons,
                reasons=';'.join(reasons) or 'passes_v1_secondary_quality',
                pulse_ids=';'.join(str(p.get('pulse_id', '')) for p in group)))
    return out
