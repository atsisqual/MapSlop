import importlib.util,sys,unittest
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
spec=importlib.util.spec_from_file_location("clean",Path(sys.path[0])/"clean-orthophoto.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CleanTests(unittest.TestCase):
    def test_raster_orientation(self):
        p=Polygon([(1,2),(3,2),(3,4),(1,4)])
        r=m.raster([p],(10,10),0,0,.5)
        self.assertEqual(r.sum(),16)
        self.assertTrue(r[4:8,2:6].all())
        self.assertFalse(r[:4].any())
    def test_fill_does_not_use_wrong_surface(self):
        a=np.zeros((40,40,3),np.uint8);a[:,:20]=[80,80,80];a[:,20:]=[15,100,10]
        paved=np.zeros((40,40),bool);paved[:,:20]=True
        mask=np.zeros_like(paved);mask[10:20,8:15]=True;mask[20:30,25:32]=True
        a[mask]=[255,0,0]
        out,report=m.fill_rgb(a,mask,paved)
        self.assertTrue(np.array_equal(out[~mask],a[~mask]))
        self.assertLess(np.abs(out[13:17,10:13].astype(int)-80).mean(),5)
        self.assertLess(np.abs(out[23:27,27:30].astype(int)-[15,100,10]).mean(),5)
        self.assertGreater(report["paved"]["pixels"],0)
    def test_visual_gate_and_bounded_mask(self):
        rng=np.random.default_rng(42)
        a=rng.integers(0,255,(96,96,3),dtype=np.uint8)
        msk=np.zeros((96,96),bool);msk[5:12,5:20]=True;msk[30:90,30:90]=True
        small,rows=m.bounded_components(msk)
        self.assertEqual(len(rows),1);self.assertFalse(small[40,40])
        b=a.copy();b[small]=0
        self.assertTrue(m.visual_metrics(a,b,small)["unmasked_exact"])
        b[40:80,40:80]=0
        self.assertGreater(m.visual_metrics(a,b,small)["local_variance_relative_change"],.01)
    def test_white_proxy(self):
        a=np.full((100,100,3),80,np.uint8);a[35:43,35:52]=230
        allow=np.ones((100,100),bool);exclude=np.zeros_like(allow)
        hit,rows=m.white_objects(a,allow,exclude)
        self.assertTrue(rows);self.assertTrue(hit[38,40])
        exclude[30:50,30:60]=True
        hit,_=m.white_objects(a,allow,exclude)
        self.assertFalse(hit.any())
    def test_vehicle_proxy_conservative(self):
        a=np.zeros((40,40),np.uint16);a[8:12,8:17]=3;a[20:34,20:34]=3
        allowed=np.ones_like(a,bool);exclude=np.zeros_like(allowed);exclude[20:34,20:34]=True
        r,rows=m.vehicle_candidates(a,allowed,exclude,.5)
        self.assertEqual(len(rows),1)
        self.assertTrue(r[8:12,8:17].all())
        self.assertFalse((r&exclude).any())
        self.assertFalse(r[20:34,20:34].any())
if __name__=="__main__":unittest.main()
