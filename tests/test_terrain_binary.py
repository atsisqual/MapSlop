import unittest
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from terrain_binary import encode,decode,save
from terrain_grid import synthetic_grid,validate

class BinaryTest(unittest.TestCase):
    def test_grid_roundtrip_and_gzip(self):
        t=synthetic_grid(5)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"terrain.bin"
            decoded,m=save(p,t)
            validate(decoded)
            self.assertLess(max(abs(a-b) for a,b in zip(t["heights"],decoded["heights"])),0.00001)
            self.assertEqual(m["bytes"],p.stat().st_size)
            self.assertLess(m["gzip_bytes"],m["bytes"])
            with self.assertRaises(ValueError):decode(p.read_bytes()[:-1])
    def test_tin_roundtrip(self):
        t={"kind":"tin","vertices":[0.,0.,0.,1.,1.,0.,0.,2.,1.,1.,3.,1.],"triangles":[0,2,1,1,2,3]}
        self.assertEqual(decode(encode(t)),t)
        with self.assertRaises(ValueError):decode(b"bad"+encode(t))
