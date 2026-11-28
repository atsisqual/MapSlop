import importlib.util,sys,tempfile,unittest,json,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"tools"/(name+".py"))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
a=load("asset-pipeline")
class AssetTests(unittest.TestCase):
    def test_similarity_with_independent_control(self):
        x=np.array([[0,0,0],[2,0,0],[0,1,0],[0,0,3]],float);R=np.array([[0,0,1],[0,1,0],[-1,0,0]])
        q=np.array([[2,3,4]]);y=lambda x:2*(x@R.T)+[8,4,-1]
        r=a.similarity(x,y(x),q,y(q));self.assertTrue(r["pass"]);self.assertAlmostEqual(r["scale"],2)
        self.assertFalse(a.similarity(x,y(x),q,y(q)+[1,0,0])["pass"])
        with self.assertRaises(ValueError):a.similarity([[0,0,0],[1,0,0],[2,0,0]],[[0,0,0],[1,0,0],[2,0,0]],q,q)
    def test_glb_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);j={"asset":{"version":"2.0"},"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],"meshes":[{"primitives":[{"attributes":{"POSITION":0}}]}],"buffers":[{"byteLength":36}],"bufferViews":[{"buffer":0,"byteLength":36}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","min":[0,0,0],"max":[1,1,0]}]}
            payload=struct.pack("<9f",0,0,0,1,0,0,0,1,0);rest=struct.pack("<I4s",len(payload),b"BIN\0")+payload
            a.write_glb(p/"src.glb",j,rest);M=np.eye(4);M[:3,3]=[1,2,3]
            a.align_glb(p/"src.glb",p/"out.glb",M);out,b=a.read_glb(p/"out.glb")
            self.assertEqual(b,rest);self.assertEqual(out["nodes"][-1]["matrix"][12:15],[1,2,3])
            manifest={"source_type":"synthetic","license":"MIT","author":"test","reviewed_by":"CI","source_url_or_archive":"fixture","files":{"src.glb":a.sha(p/"src.glb")}}
            (p/"manifest.json").write_text(json.dumps(manifest));a.provenance(p,p/"manifest.json")
            manifest["files"]["src.glb"]="0"*64;(p/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):a.provenance(p,p/"manifest.json")
    def test_tile_boxes_and_paths(self):
        t=a.tile_set([{"uri":"one.glb","bounds":[[0,0,-5],[2,4,-1]]},{"uri":"two.glb","bounds":[[2,0,-1],[6,2,3]]}])
        self.assertEqual(t["root"]["children"][0]["boundingVolume"]["box"][:3],[1,3,2])
        with self.assertRaises(ValueError):a.tile_set([{"uri":"../bad.glb","bounds":[[0,0,0],[1,1,1]]}])
    def test_inpainting(self):
        m=load("inpaint-local");yy,xx=np.indices((96,96));rgb=np.stack([80+xx,60+yy,70+xx//2],axis=2).astype(np.uint8)
        mask=np.zeros((96,96),bool);mask[36:49,30:53]=True;damaged=rgb.copy();damaged[mask]=255
        for method in ("telea","ns"):
            out,r=m.compare(rgb,damaged,mask,method)
            self.assertTrue(r["unmasked_exact"]);self.assertLess(r["masked_mae"],15)
        with self.assertRaises(ValueError):m.inpaint(rgb,mask,"lama")
        big=np.zeros_like(mask);big[:80,:80]=True
        with self.assertRaises(ValueError):m.inpaint(rgb,big,"telea")
if __name__=="__main__":unittest.main()
