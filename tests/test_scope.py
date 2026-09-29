"""Protect the user-mandated sample population from silent reinclusion."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from muones.scope import in_scope, require_event, config
from test_analysis import synthetic
from muones.filters import classify


class ScopeTests(unittest.TestCase):
    def test_path_and_length_both_required(self):
        source='Datos/Med_con_Decaimientos/PAblo/run.txt'
        self.assertTrue(in_scope(source,1024))
        self.assertFalse(in_scope(source,300))
        self.assertFalse(in_scope('Datos/eficiencia/run.txt',1024))
        self.assertFalse(in_scope('Datos/Med_con_Decaimientos_extra/run.txt',1024))
        self.assertFalse(in_scope('Datos/Med_con_Decaimientos/../eficiencia/run.txt',1024))

    def test_300_never_reaches_pulse_analysis(self):
        e=synthetic(300);e.source='Datos/Med_con_Decaimientos/test.txt'
        with self.assertRaises(ValueError):require_event(e)
        r,pp,gg=classify(e,config())
        self.assertEqual(pp,[]);self.assertEqual(gg,[])
        self.assertIn('unexpected_sample_count',r['count_reasons'])


if __name__=='__main__':unittest.main()
