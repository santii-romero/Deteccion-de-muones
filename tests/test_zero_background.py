"""Check the finite-window sufficient statistic and sample weighting."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import numpy as np
from selection_helpers import beta_from_mean, mean_offset, make_data
from muones.lifetime import fit


class ZeroBackgroundTests(unittest.TestCase):
    def test_sufficient_statistic_recovers_beta_including_boundary(self):
        beta = np.array([0., 1e-8, .5, 5., 40.])
        recovered = beta_from_mean(mean_offset(beta, 1.28), 1.28)
        np.testing.assert_allclose(recovered, beta, atol=1e-8)
        self.assertEqual(float(beta_from_mean(.7, 1.28)), 0.)

    def test_split_acquisitions_do_not_double_weight_counts(self):
        u = (np.arange(700) + .5) / 700
        t = .12 - 2.2 * np.log1p(-u * (-np.expm1(-1.28 / 2.2)))
        rows = [dict(delay_ns=x * 1000) for x in t]
        pooled = fit([make_data(rows, 'pooled')])
        split = fit([make_data(rows[:200], 'small'), make_data(rows[200:], 'large')])
        self.assertAlmostEqual(pooled['tau_us'], split['tau_us'], places=5)
        self.assertAlmostEqual(pooled['nll'] - split['nll'],
            700 - 700 * np.log(700) - (200 - 200 * np.log(200) + 500 - 500 * np.log(500)), places=7)
        self.assertEqual([y['signal'] for y in split['yields']], [200., 500.])
        self.assertTrue(all(y['background'] == 0 and y['w'] == 1 for y in split['yields']))


if __name__ == '__main__':
    unittest.main()
