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
        self.assertTrue(np.all(out[13:17,10:13]==[80,80,80]))
        self.assertTrue(np.all(out[23:27,27:30]==[15,100,10]))
        self.assertGreater(report["paved"]["pixels"],0)
    def test_vehicle_proxy_conservative(self):
        a=np.zeros((40,40),np.uint16);a[8:12,8:17]=3;a[20:34,20:34]=3
        allowed=np.ones_like(a,bool);exclude=np.zeros_like(allowed);exclude[20:34,20:34]=True
        r,rows=m.vehicle_candidates(a,allowed,exclude,.5)
        self.assertEqual(len(rows),1)
        self.assertTrue(r[8:12,8:17].all())
        self.assertFalse((r&exclude).any())
        self.assertFalse(r[20:34,20:34].any())
if __name__=="__main__":unittest.main()
