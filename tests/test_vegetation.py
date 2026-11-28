import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from terrain_grid import ORIGIN,KX,KY
spec=importlib.util.spec_from_file_location("vegetation",Path(sys.path[0])/"build-dgt-vegetation.py")
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def cos(code="5.1.1.6"):
    ring=[[ORIGIN[1]+x/KX,ORIGIN[0]-z/KY] for x,z in [(-1,-1),(12,-1),(12,12),(-1,12),(-1,-1)]]
    return {"features":[{"geometry":{"type":"Polygon","coordinates":[ring]},"properties":{"cos25v1_n4_c":code}}]}

class VegetationTests(unittest.TestCase):
    def setUp(self):
        self.h=np.zeros((10,10))
        self.n=np.zeros((10,10),dtype=int)
        self.h[4,4]=8
        self.n[4,4]=3

    def test_height_and_cos(self):
        trees,rej,cells=v.candidates(self.h,self.n,0,0,box(20,20,21,21),cos())
        self.assertEqual(cells,1)
        self.assertEqual(len(trees),1)
        self.assertEqual(trees[0]["height_m"],8)
        self.assertEqual(trees[0]["cos_code"],"5.1.1.6")
        self.assertEqual(trees[0]["class"],5)

    def test_trunk_buffer_and_crown_overhang(self):
        trees,rej,_=v.candidates(self.h,self.n,0,0,box(5,4,6,5),cos())
        self.assertEqual(trees,[])
        self.assertEqual(rej["road_or_building_trunk_overlap"],1)
        trees,rej,_=v.candidates(self.h,self.n,0,0,box(5.1,4,6,5),cos())
        self.assertEqual(len(trees),1)
        self.assertGreater(trees[0]["crown_radius_proxy_m"],.6)
        self.assertNotIn("road_or_building_trunk_overlap",rej)
        trees,rej,_=v.candidates(self.h,self.n,0,0,box(4,4,5,5),cos())
        self.assertEqual(trees,[])
        self.assertEqual(rej["road_or_building_trunk_overlap"],1)

    def test_water_and_road_cos(self):
        for code in ("9.1.1.1","1.5.1.1"):
            trees,rej,_=v.candidates(self.h,self.n,0,0,box(20,20,21,21),cos(code))
            self.assertEqual(trees,[])
            self.assertEqual(rej["cos_road_or_water"],1)

    def test_minimum_returns(self):
        self.n[4,4]=2
        trees,_,cells=v.candidates(self.h,self.n,0,0,box(20,20,21,21),cos())
        self.assertEqual((trees,cells),([],0))

    def test_plateau_suppression(self):
        self.h[4,5]=8
        self.n[4,5]=3
        trees,rej,_=v.candidates(self.h,self.n,0,0,box(20,20,21,21),cos())
        self.assertEqual(len(trees),1)
        self.assertEqual(rej["nearer_higher_peak"],1)

if __name__=="__main__":
    unittest.main()
