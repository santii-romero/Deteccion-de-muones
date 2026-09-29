"""Protect single-waveform timing and staged relaxation semantics."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from selection_helpers import allowed, choose


class InclusionTests(unittest.TestCase):
    def test_prompt3_relaxation_does_not_relax_secondary_quality(self):
        e = {'count_status': 'accepted', 'decay_status': 'ambiguous'}
        p = [{'channel': '2', 'status': 'accepted'}]
        g = {'status': 'ambiguous', 'reasons': 'prompt3_present_control_sample'}
        self.assertTrue(allowed(e, g, p, 1))
        g['reasons'] += ';secondary_quality_uncertain'
        self.assertFalse(allowed(e, g, p, 1))
        self.assertTrue(allowed(e, g, p, 4))

    def test_soft_quality_requires_nonexcluded_secondary_channel(self):
        e = {'count_status': 'accepted', 'decay_status': 'ambiguous'}
        g = {'status': 'ambiguous', 'reasons': 'no_clean_secondary_ch2_or_ch3;secondary_quality_uncertain'}
        p = [{'channel': '1', 'status': 'accepted'}, {'channel': '2', 'status': 'excluded'}]
        self.assertFalse(allowed(e, g, p, 4))
        self.assertTrue(allowed(e, g, p, 5))

    def test_peak_choice_precedes_window_and_returns_one_group(self):
        options = [{'group_id': '0', 'delay_ns': '80', 'peak_amplitude_ch23_mV': '200'},
                   {'group_id': '1', 'delay_ns': '800', 'peak_amplitude_ch23_mV': '100'}]
        self.assertIs(choose(options, 'strongest'), options[0])
        self.assertIs(choose(options, 'earliest'), options[0])
        options[1]['peak_amplitude_ch23_mV'] = '300'
        self.assertIs(choose(options, 'strongest'), options[1])
        self.assertIs(choose(options, 'earliest'), options[0])


if __name__ == '__main__':
    unittest.main()
