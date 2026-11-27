import importlib.util
import sys
from pathlib import Path
import unittest
import numpy as np
from scipy.spatial import Delaunay
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from terrain_grid import ORIGIN,KX,KY,grid_shape
from terrain_tin import TinSampler,validate_tin
spec=importlib.util.spec_from_file_location("roof_cut",Path(__file__).resolve().parents[1]/"tools/cut-roof-terrain.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
    x0,z0,nx,nz=grid_shape(.5)
    x1,z1=x0+(nx-1)*.5,z0+(nz-1)*.5
    xy=np.array([(x,z) for x in range(-8,9) for z in range(-8,9)]+[(x0,z0),(x0,z1),(x1,z0),(x1,z1)],dtype=float)
    f=Delaunay(xy).simplices.copy()
    a,b,c=xy[f[:,0]],xy[f[:,1]],xy[f[:,2]]
    signed=(b[:,0]-a[:,0])*(c[:,1]-a[:,1])-(b[:,1]-a[:,1])*(c[:,0]-a[:,0])
    f[signed>0]=f[signed>0][:,[0,2,1]]
    v=np.column_stack((xy[:,0],.1*xy[:,0],xy[:,1])).astype(np.float32)
    t=validate_tin(dict(kind="tin",source="SYNTHETIC TEST TERRAIN",origin_lat_lon=list(ORIGIN),base=100.,x0=x0,z0=z0,nx=nx,nz=nz,cell=.5,vertices=v.ravel().tolist(),triangles=f.astype(int).ravel().tolist()))
    def way(i,points,tags):
        return {"id":i,"type":"way","geometry":[{"lon":ORIGIN[1]+x/KX,"lat":ORIGIN[0]-z/KY} for x,z in points],"tags":tags}
    ring=[(-2,-2),(2,-2),(2,2),(-2,2),(-2,-2)]
    src={"roof":[-2,-.23,-2,2,-.23,-2,2,-.23,2,-2,-.23,-2,2,-.23,2,-2,-.23,2]}
    return t,{"elements":[way(m.TARGET,ring,{"building":"house"})]},src,way

class RoofCutTests(unittest.TestCase):
    def test_cut_preserves_exterior_and_clears_roof(self):
        t,osm,src,_=fixture()
        report={}
        cut=m.attempt(t,osm,src,report)
        self.assertGreaterEqual(report["post_cut_roof_clearance_min_m"],.15)
        self.assertLessEqual(report["max_cut_depth_m"],m.MAX_DEPTH)
        self.assertGreater(report["outside_faces_unchanged"],0)
        before,after=TinSampler(t),TinSampler(cut)
        for x,z in [(-6,-6),(6,6),(0,7),(7,0)]:
            self.assertAlmostEqual(before(x,z),after(x,z),places=6)
    def test_road_guard(self):
        t,osm,src,way=fixture()
        osm["elements"].append(way(42,[(-8,2),(8,2)],{"highway":"residential"}))
        with self.assertRaisesRegex(ValueError,"protected OSM way"):
            m.attempt(t,osm,src,{})
