import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from muones.finite_window import density,fit,expected_offset
from muones.lifetime import fit as common_fit,exponential_pdf


class FiniteWindowTests(unittest.TestCase):
    def test_density_normalizes_different_windows_and_zero_rate(self):
        for beta in (0.,1e-8,.5,4.):
            for upper in (1.4,1.46,1.50):
                t=np.linspace(.12,upper,20001)
                self.assertAlmostEqual(np.trapezoid(density(t,beta,.12,upper),t),1.,places=7)
        self.assertEqual(density(np.array([.1,1.51]),.5,.12,1.5).tolist(),[0.,0.])

    def test_common_window_recovers_existing_likelihood_and_intervals(self):
        u=(np.arange(500)+.5)/500
        t=.12-2.2*np.log1p(-u*(-np.expm1(-1.28/2.2)))
        old=common_fit([dict(run='one',t=t,lo=.12,hi=1.4,off=0,alpha=0.,pure_signal=True)])
        new=fit(t,1.4)
        # The legacy bounded optimizer has a looser stopping tolerance than
        # the new score root; agreement is required well below one sample ns.
        np.testing.assert_allclose(old['tau_us'],new['tau_us'],rtol=5e-6)
        for ci in ('68','95'):np.testing.assert_allclose(old['intervals_us'][ci],new['intervals_us'][ci],rtol=1e-6)

    def test_variable_windows_recover_known_mean_not_untruncated_mean(self):
        hi=np.array([1.40,1.46,1.49,1.50]*125)
        beta=1/2.2
        # Every observation is the known conditional expectation for its window.
        t=.12+expected_offset(beta,hi-.12)
        result=fit(t,hi)
        self.assertAlmostEqual(result['tau_us'],2.2,places=8)
        self.assertLess(t.mean(),.9)

    def test_rejects_exceeding_record_and_retains_infinite_tau_boundary(self):
        with self.assertRaises(ValueError):fit([1.5],[1.48])
        result=fit([1.2,1.3],[1.4,1.4])
        self.assertIsNone(result['tau_us'])
        self.assertIsNone(result['intervals_us']['95'][1])


if __name__=='__main__':unittest.main()
