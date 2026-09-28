"""Signal-only conditional likelihood with a known upper limit per event.

All times are microseconds. Upper limits describe observed record geometry,
not a measured selection efficiency. The event weights are one.
"""
import numpy as np
from scipy.optimize import brentq, minimize_scalar
from scipy.special import exprel


def log_normalization(beta, width):
    width = np.asarray(width, dtype=float)
    return np.log(width) + np.log(exprel(-np.asarray(beta) * width))


def density(t, beta, lo, hi):
    t, hi = np.broadcast_arrays(np.asarray(t, dtype=float), np.asarray(hi, dtype=float))
    if np.any(hi <= lo) or beta < 0:
        raise ValueError('Invalid observation window or decay rate')
    value = np.exp(-beta * (t - lo) - log_normalization(beta, hi - lo))
    return np.where((t >= lo) & (t <= hi), value, 0.)


def expected_offset(beta, width):
    beta, width = np.broadcast_arrays(np.asarray(beta, dtype=float), np.asarray(width, dtype=float))
    small = np.abs(beta * width) < 1e-3
    out = width / 2 - beta * width**2 / 12 + beta**3 * width**4 / 720
    large = np.zeros_like(out)
    np.divide(1., beta, out=large, where=~small)
    correction = np.zeros_like(out)
    np.divide(width, np.expm1(beta * width), out=correction, where=~small)
    return np.where(small, out, large - correction)


def fit(t, hi, lo=.12):
    t = np.asarray(t, dtype=float)
    hi = np.broadcast_to(np.asarray(hi, dtype=float), t.shape)
    if t.ndim != 1 or not len(t) or not np.isfinite(t).all() or not np.isfinite(hi).all():
        raise ValueError('Finite nonempty event vectors required')
    if np.any(hi <= lo) or np.any(t < lo) or np.any(t > hi):
        raise ValueError('Events outside their observation windows')
    width = hi - lo; total = float(np.sum(t - lo))
    def nll(beta):
        return float(beta * total + np.sum(log_normalization(beta, width)))
    def score(beta):
        return total - float(np.sum(expected_offset(beta, width)))
    beta = 0. if score(0.) >= 0 else brentq(score, 0., 100., xtol=1e-12)
    optimum = nll(beta)
    # Independent optimizer of the conditional density, excluding beta=0 exactly.
    opt = minimize_scalar(nll, bounds=(0.,100.), method='bounded', options={'xatol':1e-10})
    optimizer_beta = min([0., float(opt.x),100.], key=nll)
    assert abs(optimizer_beta - beta) < 3e-6
    intervals = {}
    for name, delta in [('68',.5),('95',1.920729410347062)]:
        target = lambda b: nll(b) - optimum - delta
        low = 0. if target(0.) <= 0 else brentq(target,0.,beta)
        high = brentq(target,beta,100.)
        intervals[name] = [1/high,1/low if low else None]
    return dict(events=len(t),beta_per_us=beta,tau_us=1/beta if beta else None,
        intervals_us=intervals,conditional_nll=optimum,
        minus2logL_at_infinite_tau=2*(nll(0.)-optimum), independent_optimizer_beta=optimizer_beta,
        background=0.,event_weight=1.,lower_us=float(lo),
        upper_us_range=[float(hi.min()),float(hi.max())])


def validate_local(t, hi, result, seed, draws=3000, lo=.12):
    """Fixed-record-window simulations; acceptance and waveform shape not tested."""
    t = np.asarray(t, dtype=float); hi = np.broadcast_to(np.asarray(hi,dtype=float),t.shape)
    widths = hi - lo; beta = result['beta_per_us']; rng = np.random.default_rng(seed)
    unique, counts = np.unique(widths,return_counts=True)
    u = rng.random((draws,len(t)))
    offsets = -np.log1p(-u * (-np.expm1(-beta * widths))) / beta if beta else u * widths
    totals = offsets.sum(axis=1)
    lower = np.zeros(draws); upper = np.full(draws,100.)
    for _ in range(55):
        mid = (lower + upper) / 2
        expectation = expected_offset(mid[:,None],unique[None,:]) @ counts
        lower = np.where(expectation > totals,mid,lower)
        upper = np.where(expectation > totals,upper,mid)
    estimates = np.where(totals >= np.sum(widths)/2,0.,(lower+upper)/2)
    best = estimates * totals + log_normalization(estimates[:,None],unique[None,:]) @ counts
    truth = beta * totals + np.sum(log_normalization(beta,widths))
    lr = np.maximum(0.,2*(truth-best))
    pit = np.divide(-np.expm1(-estimates[:,None]*offsets),-np.expm1(-estimates[:,None]*widths),
                    out=offsets/widths,where=estimates[:,None]!=0)
    pit.sort(axis=1)
    def ks(sorted_pit):
        n = sorted_pit.shape[1]
        return np.maximum(np.max(np.arange(1,n+1)/n-sorted_pit,axis=1),
                          np.max(sorted_pit-np.arange(n)/n,axis=1))
    observed = -np.expm1(-beta*(t-lo))/(-np.expm1(-beta*widths)) if beta else (t-lo)/widths
    observed_ks = float(ks(np.sort(observed)[None,:])[0])
    simulated_ks = ks(pit)
    return dict(simulations=draws,seed=seed,events=len(t),generator_tau_us=result['tau_us'],
        nominal_68_coverage=float(np.mean(lr<=1.)), nominal_95_coverage=float(np.mean(lr<=3.841458820694124)),
        empirical_lr_thresholds=np.quantile(lr,[.682689492,.95]).tolist(),infinite_tau_fits=int(np.sum(estimates==0)),
        observed_pit_ks=observed_ks,refitted_pit_ks_p=(1+int(np.sum(simulated_ks>=observed_ks)))/(draws+1),
        scope='Conditional on observed counts and each record window; exponential-only, unit weights. No waveform/edge efficiency or purity calibration.')
