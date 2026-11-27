import importlib.util
import sys
import unittest
from pathlib import Path
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import Polygon,box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from building_heights import key,apply
spec=importlib.util.spec_from_file_location("calc",Path(__file__).resolve().parents[1]/"tools/build-building-heights.py")
calc=importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)

class BuildingHeightTest(unittest.TestCase):
    def test_paired_pixels_holes_and_nodata(self):
        a=np.ma.array(np.full((30,30),100.0),mask=False)
        b=np.ma.array(np.full((30,30),106.0),mask=False)
        b[12:18,12:18]=190  # courtyard, must not pollute roof statistic
        p=Polygon([(2,2),(13,2),(13,13),(2,13)],holes=[[(5.5,5.5),(9.5,5.5),(9.5,9.5),(5.5,9.5)]])
        tr=from_origin(0,15,0.5,0.5)
        stats,reason=calc.extract(p,a,b,tr)
        self.assertIsNone(reason)
        self.assertEqual(stats["delta_p75_m"],6)
        b.mask=np.ones(b.shape,dtype=bool)
        self.assertEqual(calc.extract(p,a,b,tr)[1],"no_valid_pixels")
        self.assertEqual(calc.extract(box(2,2,2.4,2.4),a,b,tr)[1],"inset_empty")
    def test_aligned_negative_and_sparse_rejected(self):
        a=np.ma.array(np.full((20,20),100.0),mask=False)
        b=np.ma.array(np.full((20,20),99.0),mask=False)
        self.assertEqual(calc.extract(box(1,1,8,8),a,b,from_origin(0,10,.5,.5))[1],"implausible_height")
    def test_exact_footprint_and_fallback(self):
        b={"osmType":"way","id":1,"ring":[0,0,3,0,3,3,0,3],"h":4,"est":1}
        r={"schema":1,"osm_sha256":"a","terrain_sha256":"b","buildings":[{"footprint_key":key(b),"method":"fallback","render_height_m":4}]}
        self.assertEqual(apply([b],r,"a","b"),0)
        self.assertEqual(b["est"],1)
        r["buildings"][0].update(method="mds_mdt",render_height_m=6,roof_relative_m=7)
        self.assertEqual(apply([b],r,"a","b"),1)
        self.assertEqual(b["h"],6)
        self.assertNotIn("est",b)
        with self.assertRaises(ValueError):apply([b],r,"a","wrong")
        with self.assertRaises(ValueError):apply([{**b,"id":2}],r,"a","b")
