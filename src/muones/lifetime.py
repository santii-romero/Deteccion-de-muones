"""Extended on/off Poisson likelihood with separate yields by run.

beta=1/tau in inverse microseconds includes beta=0 (infinite lifetime) exactly.
The signal and accidental shapes are normalized on the observed window.
For signal fraction w and total on yield T, off mean=alpha*(1-w)*T.
T is profiled analytically: (n_on+n_off)/(1+alpha*(1-w)).
"""
import numpy as np
from scipy.optimize import minimize_scalar, brentq
from scipy.special import xlogy


def exponential_pdf(t, beta, lo, hi):
    t=np.asarray(t)
    norm=(hi-lo) if abs(beta)<1e-10 else -np.expm1(-beta*(hi-lo))/beta
    return np.exp(-beta*(t-lo))/norm


def run_profile(beta, data):
    t=np.asarray(data['t']);lo=data['lo'];hi=data['hi']
    n=len(t);k=data['off'];alpha=data['alpha']
    grid=data.get('eff_grid');eff=data.get('eff')
    if grid is None:
        fs=exponential_pdf(t,beta,lo,hi); fb=np.full(n,1/(hi-lo))
    else:
        # Dense deterministic trapezoidal quadrature for injection sensitivity only.
        x=np.linspace(lo,hi,1281);y=np.interp(x,grid,eff)
        et=np.interp(t,grid,eff)
        fs=et*np.exp(-beta*(t-lo))/np.trapezoid(y*np.exp(-beta*(x-lo)),x)
        fb=et/np.trapezoid(y,x)
    def evaluate(w):
        total=(n+k)/(1+alpha*(1-w))
        muoff=alpha*(1-w)*total
        density=w*fs+(1-w)*fb
        nll=total+muoff-xlogy(n,total)-xlogy(k,muoff)-np.log(density).sum()
        return float(nll),total
    if n+k==0:return 0.,dict(signal=0.,background=0.,off_mean=0.,w=0.)
    if data.get('pure_signal',False):w=1.
    else:
        sol=minimize_scalar(lambda w:evaluate(w)[0],bounds=(0,1),method='bounded',options={'xatol':1e-10})
        w=min([0.,1.,sol.x],key=lambda x:evaluate(x)[0])
    nll,total=evaluate(w)
    return nll,dict(signal=total*w,background=total*(1-w),off_mean=alpha*total*(1-w),w=w)


def fit(data):
    def profile(beta):return sum(run_profile(beta,d)[0] for d in data)
    grid=np.unique(np.r_[np.linspace(0,12,121),np.geomspace(12.1,100,40)])
    vals=np.array([profile(b) for b in grid]);j=int(np.argmin(vals))
    opt=minimize_scalar(profile,bounds=(grid[max(0,j-1)],grid[min(len(grid)-1,j+1)]),method='bounded')
    beta=min([0.,opt.x,100.],key=profile);nll=profile(beta)
    intervals={}
    for label,delta in [('68',.5),('95',1.920729410347062)]:
        target=lambda b:profile(b)-nll-delta
        lower_beta=0. if target(0)<=0 else brentq(target,0,beta)
        upper_beta=brentq(target,beta,100) if target(100)>0 else 100.
        intervals[label]=[1/upper_beta,1/lower_beta if lower_beta else None]
    yields=[dict(run=d['run'],on=len(d['t']),off=d['off'],alpha=d['alpha'],**run_profile(beta,d)[1]) for d in data]
    return dict(beta_per_us=beta,tau_us=1/beta if beta else None,nll=nll,intervals_us=intervals,
        minus2logL_at_infinite_tau=2*(profile(0)-nll),yields=yields,
        profile=[dict(beta_per_us=float(b),tau_us=float(1/b) if b else None,twice_delta_nll=float(2*(v-nll)))
                 for b,v in zip(grid,vals)])
