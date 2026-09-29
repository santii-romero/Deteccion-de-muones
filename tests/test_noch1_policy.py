import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from selection_helpers import regroup
from muones.finite_window import density
from muones.lifetime import exponential_pdf
import numpy as np


class NoCH1PolicyTests(unittest.TestCase):
    def test_bad_late_ch1_neither_vetoes_nor_sets_secondary_time(self):
        pulses = [dict(pulse_id='0', channel=2, time_ns=500., amplitude_mV=100., status='accepted', reasons=''),
                  dict(pulse_id='1', channel=1, time_ns=505., amplitude_mV=50., status='excluded', reasons='narrow_or_single_sample')]
        g = regroup(pulses, 200.)[0]
        self.assertTrue(g['eligible_without_ch1_veto'])
        self.assertEqual(g['delay_ns'], 300.)
        self.assertFalse(g['selected'])

    def test_secondary_quality_is_still_pending(self):
        pulses = [dict(pulse_id='0', channel=2, time_ns=500., amplitude_mV=100., status='accepted', reasons=''),
                  dict(pulse_id='1', channel=3, time_ns=503., amplitude_mV=60., status='ambiguous', reasons='below_analysis_threshold')]
        g = regroup(pulses, 200.)[0]
        self.assertFalse(g['eligible_without_ch1_veto'])
        self.assertTrue(g['has_clean_target'])

    def test_variable_window_density_reduces_to_common_window(self):
        t = np.array([.12, .5, 1.4])
        for beta in (0., .5, 2.):
            np.testing.assert_allclose(density(t, beta, .12, np.full(3, 1.4)), exponential_pdf(t, beta, .12, 1.4))


if __name__ == '__main__': unittest.main()
