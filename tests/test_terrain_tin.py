import unittest
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from terrain_tin import from_raster, TinSampler, validate_tin, refine_roads, accepts_refinement
from terrain_grid import grid_shape

class TinTest(unittest.TestCase):
    def test_asymmetric_raster_and_faces(self):
        bounds=(-10,-7,10,9)
        x0,z0,nx,nz=grid_shape(0.5,bounds)
        x,z=np.meshgrid(x0+np.arange(nx)*0.5,z0+np.arange(nz)*0.5)
        h=0.3*x-0.1*z+0.8*np.sin(x/2)*np.cos(z/3)
        t=from_raster(h,x0,z0,100,"SYNTHETIC TEST TERRAIN",bounds)
        self.assertLessEqual(t["library_error_m"],0.25+1e-6)
        s=TinSampler(t)
        for j in range(0,nz,3):
            for i in range(0,nx,3):
                self.assertLessEqual(abs(s(x[j,i],z[j,i])-h[j,i]),0.252)
        self.assertLess(len(t["vertices"])//3,nx*nz)
        with self.assertRaises(ValueError):
            validate_tin({**t,"triangles":[999999,1,2]},bounds)

    def test_road_refinement_and_final_raster_check(self):
        bounds=(-12,-12,12,12)
        x0,z0,nx,nz=grid_shape(0.5,bounds)
        x,z=np.meshgrid(x0+np.arange(nx)*0.5,z0+np.arange(nz)*0.5)
        def ref(x,z):
            return 100+0.1*x-0.08*z+0.9*np.exp(-((z-0.8)/0.7)**2)*np.sin(x/1.7)
        h=ref(x,z)-100
        t=from_raster(h,x0,z0,100,"SYNTHETIC TEST TERRAIN",bounds)
        road=np.column_stack((np.linspace(-10,10,81),np.full(81,0.8)))
        result=refine_roads(t,h,road,ref(road[:,0],road[:,1]),road,ref,bounds)
        s=TinSampler(result)
        self.assertLessEqual(max(abs(100+s(a,b)-c) for (a,b),c in zip(road,ref(road[:,0],road[:,1]))),0.5)
        self.assertLessEqual(result["raster_max_abs_m"],0.5)
        self.assertEqual(result["refinement"]["raster_samples"],nx*nz)
        self.assertGreaterEqual(result["refinement"]["corridor_added_vertices"],0)
        rounds=result["refinement"]["rounds"]
        accepted=[r for r in rounds if r["accepted"]]
        self.assertTrue(accepted)
        maxima=[r["road_max_abs_m"] for r in accepted]
        self.assertEqual(maxima,sorted(maxima,reverse=True))
        self.assertEqual(accepted[-1]["vertices"],len(result["vertices"])//3)
        self.assertEqual(accepted[-1]["raster_max_abs_m"],result["raster_max_abs_m"])
        self.assertEqual(len(accepted),result["refinement"]["accepted_rounds"])
        self.assertEqual(len(rounds)-len(accepted),result["refinement"]["rejected_rounds"])

    def test_reject_road_error_regression(self):
        # Reproduce the maxima observed in run 46056885609, including a rejected proposal.
        previous=None
        decisions=[]
        accepted=[]
        for road,raster in [(0.586451,0.7),(0.424830,0.6),(0.662954,0.4),(0.350236,0.45)]:
            ok=accepts_refinement(road,raster,previous)
            decisions.append(ok)
            if ok:
                previous=(road,raster)
                accepted.append(road)
        self.assertEqual(decisions,[True,True,False,True])
        self.assertEqual(accepted,sorted(accepted,reverse=True))
        self.assertFalse(accepts_refinement(0.35,0.6,(0.35,0.5)))
        self.assertTrue(accepts_refinement(0.35,0.4,(0.35,0.5)))
        self.assertFalse(accepts_refinement(float("nan"),0.4,previous))
