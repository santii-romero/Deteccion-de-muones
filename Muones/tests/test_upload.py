"""The separate five-column file must not be parsed as ordinary Event blocks."""
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from muones.upload import blocks

ROOT=Path(__file__).resolve().parents[1]
(ROOT/"tmp").mkdir(exist_ok=True)
HEAD='tiempo [ns]\tcanal 1 [mV]\tcanal 2 [mV]\tcanal 3 [mV]\t#decaimiento\n'


class UploadParserTests(unittest.TestCase):
    def test_boundaries_and_columns(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
            p=Path(d)/'test.txt'
            p.write_text(HEAD+'0\t-1\t-2\t-3\t1\n1.66\t-2\t-3\t-4\t1\n0\t-1\t-2\t-3\t2\n',encoding='utf-8')
            rr=list(blocks(p))
            self.assertEqual([(k,len(a),first,last) for k,first,last,a in rr],[(1,2,2,3),(2,1,4,4)])
            self.assertEqual(rr[0][3][1,0],1.66)

    def test_malformed_and_nonfinite_fail_closed(self):
        for payload in ['0\t-1\t-2\t1\n','0\t-1\tnan\t-3\t1\n']:
            with self.subTest(payload=payload),tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
                p=Path(d)/'bad.txt';p.write_text(HEAD+payload,encoding='utf-8')
                with self.assertRaises(ValueError):list(blocks(p))


if __name__=='__main__':unittest.main()
