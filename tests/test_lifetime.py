"""Numerical and regression checks for truncated on/off inference."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import unittest
import numpy as np
from scipy.optimize import minimize
from scipy.special import xlogy
from muones.lifetime import exponential_pdf, run_profile, fit
from muones.background import windows, secondary_groups


class LifetimeTests(unittest.TestCase):
    def test_truncation_normalization_including_flat_limit(self):
        x=np.linspace(.12,1.4,100001)
        for beta in [0.,1e-12,.5,5.,100.]:
            self.assertAlmostEqual(np.trapezoid(exponential_pdf(x,beta,.12,1.4),x),1.,places=6)

    def test_truncated_quantiles_recover_time_constant(self):
        u=(np.arange(4000)+.5)/4000;lo=.12;hi=1.4;tau=2.2
        t=lo-tau*np.log1p(-u*(-np.expm1(-(hi-lo)/tau)))
        result=fit([dict(run='synthetic1024',t=t,lo=lo,hi=hi,off=0,alpha=0,pure_signal=True)])
        self.assertAlmostEqual(result['tau_us'],tau,places=4)
        self.assertLess(np.mean(t),tau/2)  # A naive mean is seriously biased here.

    def test_profile_matches_independent_yield_optimization(self):
        d=dict(t=np.linspace(.13,1.3,30),lo=.12,hi=1.4,off=2,alpha=.04)
        beta=1.7;nll,y=run_profile(beta,d)
        fs=exponential_pdf(d['t'],beta,d['lo'],d['hi']);fb=1/(d['hi']-d['lo'])
        def f(x):
            s,b=x
            return s+b+d['alpha']*b-np.log(s*fs+b*fb).sum()-xlogy(d['off'],d['alpha']*b)
        sol=minimize(f,[10.,20.],bounds=[(0,None),(1e-10,None)],method='Nelder-Mead',options={'xatol':1e-9})
        self.assertAlmostEqual(nll,sol.fun,places=7)

    def test_symmetric_windows_honor_left_edge(self):
        cfg={'matched_lag_ns':[120,170],'fit_ns':[120,1400],'edge_ns':35}
        self.assertEqual(windows({'t0_ns':190,'max_delay_ns':1473},cfg),(120,155,120,1400))

    def test_control_retains_contaminating_seed_veto(self):
        pp=[dict(channel=2,time_ns=60.,status='accepted',pulse_id=0),
            dict(channel=1,time_ns=63.,status='ambiguous',pulse_id=1),
            dict(channel=3,time_ns=355.,status='accepted',pulse_id=2)]
        g=secondary_groups(pp,210.)
        self.assertFalse(g[0]['selected']);self.assertIn('ch1_seed_veto',g[0]['reasons'])
        self.assertTrue(g[1]['selected'])


if __name__=='__main__':unittest.main()
