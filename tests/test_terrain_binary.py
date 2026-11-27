import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from terrain_binary import encode,decode,save,assert_same_geometry
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

    def test_compact_lossless_and_node_decoder(self):
        t={"kind":"tin","vertices":[0.,-0.1234567,0.,1.01,1.98765,0.,0.,2.25,1.,1.01,-3.5,1.],
           "triangles":[0,2,1,1,2,3]}
        raw=encode(t,compact=True)
        decoded=decode(raw)
        assert_same_geometry(t,decoded)
        with self.assertRaises(ValueError):
            decode(raw[:-1])
        with self.assertRaises(ValueError):
            encode({**t,"vertices":[0.003,*t["vertices"][1:]]},compact=True)
        with self.assertRaises(ValueError):
            assert_same_geometry(t,{**decoded,"triangles":decoded["triangles"][::-1]})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"terrain.bin"
            p.write_bytes(raw)
            decoder=Path(__file__).resolve().parents[1]/"tools/terrain-binary.mjs"
            # Dynamic import accepts the absolute file URL supplied as argv.
            js="""const {loadTerrain}=await import(process.argv[1]);
const t=await loadTerrain(new URL(process.argv[2]));
console.log(JSON.stringify({vertices:Array.from(t.vertices),triangles:Array.from(t.triangles)}));"""
            actual=json.loads(subprocess.check_output(
                ["node","--input-type=module","-e",js,decoder.as_uri(),p.as_uri()],text=True))
            self.assertEqual(actual["vertices"],decoded["vertices"])
            self.assertEqual(actual["triangles"],decoded["triangles"])

    def test_compact_dense_mesh_smaller(self):
        import math
        n=70
        vertices=[c for z in range(n) for x in range(n)
                  for c in (x*0.5,math.sin(x/10)+math.cos(z/7),z*0.5)]
        faces=[]
        for z in range(n-1):
            for x in range(n-1):
                a=z*n+x
                faces.extend((a,a+n,a+1,a+1,a+n,a+n+1))
        t={"kind":"tin","vertices":vertices,"triangles":faces}
        with tempfile.TemporaryDirectory() as d:
            _,m=save(Path(d)/"terrain.bin",t,compact=True)
            self.assertTrue(m["exact_float32_geometry"])
            self.assertLess(m["gzip_bytes"],m["legacy_binary_gzip_bytes"])
