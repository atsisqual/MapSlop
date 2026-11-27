import unittest
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from terrain_tin import from_raster, TinSampler, validate_tin
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
