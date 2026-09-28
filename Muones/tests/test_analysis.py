"""Meaningful regression checks: corrupt files, boundaries, double pulses and locality."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import unittest
import tempfile
import json
import numpy as np
from muones.io import Event, read_events, read_indexed
from muones.filters import classify

ROOT=Path(__file__).resolve().parents[1]
(ROOT/"tmp").mkdir(exist_ok=True)
CFG=json.loads((ROOT/'config/filters_v1_1024.json').read_text())


def shape(t, center, width=4.):
    return np.exp(-.5*((t-center)/width)**2)


def synthetic(n=1024):
    t=np.arange(n)*1.66
    v=np.random.default_rng(73).normal(-7,3,(n,3))
    v[:,0]-=160*shape(t,215)
    v[:,1]-=180*shape(t,217)
    return Event('synthetic','synthetic',0,1,1,'2026-09-27 00:00:00.000',1,np.column_stack([t,v]))


class ParserTests(unittest.TestCase):
    def test_variable_length_boundaries_and_index(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
            p=Path(d)/'run_20260927_120000_idx0_selected.txt'
            p.write_text('# DRS4\nEvent #3  ts=2026-09-27 12:00:00.000  [SELECTED]\n  t[ns] u1[mV] u2[mV] u3[mV]\n0 -1 -2 -3\n1 -4 -5 -6\n\nEvent #9  ts=2026-09-27 12:00:01.000  [SELECTED]\n  t[ns] u1[mV] u2[mV] u3[mV]\n0 -7 -8 -9\n',encoding='utf-8')
            ee=list(read_events(p,ROOT))
            self.assertEqual([len(e.data) for e in ee],[2,1])
            self.assertEqual([e.event_id for e in ee],[3,9])
            e=ee[1]
            other=read_indexed(e.__dict__,ROOT)
            np.testing.assert_equal(e.data,other.data)

    def test_corrupt_row_is_flagged(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
            p=Path(d)/'a.txt'
            p.write_text('Event #1  ts=x\nt[ns] u1[mV] u2[mV] u3[mV]\n0 1 2 3\n1 2 3\n2 3 4 5 6\n',encoding='utf-8')
            e=next(read_events(p,ROOT))
            self.assertEqual(len(e.data),1)
            self.assertEqual(len(e.errors),2)

    def test_nonmonotonic_axis(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
            p=Path(d)/'a.txt'
            p.write_text('Event #1  ts=x\nt[ns] u1[mV] u2[mV] u3[mV]\n1 1 2 3\n0 2 3 4\n',encoding='utf-8')
            self.assertIn('nonmonotonic_time',next(read_events(p,ROOT)).errors)


class SelectionTests(unittest.TestCase):
    def test_prompt_and_isolated_secondary(self):
        e=synthetic(); e.data[:,2]-=140*shape(e.data[:,0],600)
        r,pp,gg=classify(e,CFG)
        self.assertEqual(r['count_status'],'accepted')
        self.assertEqual(r['decay_status'],'candidate')
        self.assertAlmostEqual(gg[0]['delay_ns'],385,delta=3)

    def test_late_artifact_preserves_count(self):
        e=synthetic(); t=e.data[:,0]
        burst=300*np.sin((t-700)*2*np.pi/12)*np.exp(-.5*((t-700)/25)**2)
        e.data[:,2]+=burst
        r,pp,gg=classify(e,CFG)
        self.assertEqual(r['count_status'],'accepted')
        self.assertTrue(any('bipolar_oscillation' in p['reasons'] for p in pp))
        self.assertNotEqual(r['decay_status'],'candidate')

    def test_single_sample_is_not_secondary(self):
        e=synthetic(); e.data[400,2]=-250
        r,pp,gg=classify(e,CFG)
        self.assertNotEqual(r['decay_status'],'candidate')
        self.assertTrue(any('narrow_or_single_sample' in p['reasons'] for p in pp))

    def test_prompt_ch3_is_control_not_stop_claim(self):
        e=synthetic(); t=e.data[:,0]
        e.data[:,3]-=170*shape(t,217)
        e.data[:,2]-=140*shape(t,600)
        r,pp,gg=classify(e,CFG)
        self.assertEqual(r['prompt3_status'],'detected')
        self.assertEqual(gg[0]['status'],'ambiguous')
        self.assertIn('prompt3_present_control_sample',gg[0]['reasons'])

    def test_secondary_near_end_remains_ambiguous(self):
        e=synthetic(); e.data[:,2]-=140*shape(e.data[:,0],1685)
        r,pp,gg=classify(e,CFG)
        self.assertNotEqual(r['decay_status'],'candidate')
        self.assertTrue(any('edge_truncated' in p['reasons'] for p in pp))

    def test_invalid_record_not_classified(self):
        e=synthetic(299)
        r,_,_=classify(e,CFG)
        self.assertEqual(r['count_status'],'excluded')
        self.assertIn('unexpected_sample_count',r['count_reasons'])

    def test_late_ch1_ch2_direction_is_ambiguous(self):
        e=synthetic(); t=e.data[:,0]
        e.data[:,1]-=140*shape(t,600);e.data[:,2]-=140*shape(t,597)
        r,_,gg=classify(e,CFG)
        self.assertEqual(gg[0]['status'],'ambiguous')
        self.assertIn('direction_ambiguous',gg[0]['reasons'])


if __name__=='__main__':
    unittest.main()
