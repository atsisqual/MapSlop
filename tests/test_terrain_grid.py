import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import sys

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform

TOOLS=Path(__file__).resolve().parents[1]/"tools"
sys.path.insert(0,str(TOOLS))
from terrain_grid import ORIGIN, grid_shape, height_at, synthetic_grid, validate
spec=importlib.util.spec_from_file_location("dgt_terrain",TOOLS/"build-dgt-terrain.py")
dt=importlib.util.module_from_spec(spec)
spec.loader.exec_module(dt)

class TerrainGridTest(unittest.TestCase):
    def setUp(self):
        self.crs="EPSG:3763"
        x,y=transform("EPSG:4326",self.crs,[ORIGIN[1]],[ORIGIN[0]])
        self.affine=from_origin(x[0]-50,y[0]+50,0.5,0.5)
        i,j=np.meshgrid(np.arange(200),np.arange(200))
        self.mosaic=np.ma.array(100+0.01*i+0.02*j,mask=np.zeros((200,200),dtype=bool))
        self.bounds=(-20,-20,20,20)

    def test_plane_and_origin(self):
        t=dt.build_grid(self.mosaic,self.affine,self.crs,2,self.bounds,"SYNTHETIC TEST TERRAIN")
        self.assertEqual((21,21),(t["nx"],t["nz"]))
        self.assertAlmostEqual(height_at(t,0,0),0,places=3)
        r=dt.compare(t,self.mosaic,self.affine,self.crs,self.bounds)
        self.assertEqual(r["points"],100)
        self.assertLess(r["max_abs_m"],0.005)

    def test_nodata_and_outside(self):
        bad=self.mosaic.copy()
        bad.mask[99:102,99:102]=True
        with self.assertRaisesRegex(ValueError,"NoData"):
            dt.sample(bad,self.affine,self.crs,np.array([0.0]),np.array([0.0]))
        with self.assertRaisesRegex(ValueError,"outside"):
            dt.sample(self.mosaic,self.affine,self.crs,np.array([1000.0]),np.array([0.0]))

    def test_hash_and_asset_inventory(self):
        assets=dt.expected_assets()
        self.assertEqual(len(assets),4)
        self.assertEqual(len({a["sha256"] for a in assets}),4)
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/assets[0]["name"];f.write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                dt.verify_asset(f,assets[0])

    def test_tile_resolution(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"test.tif"
            for resolution in (0.5,1):
                with rasterio.open(f,"w",driver="GTiff",count=1,width=2,height=2,dtype="float32",
                    crs=self.crs,transform=from_origin(0,0,resolution,resolution)) as ds:
                    ds.write(np.ones((2,2),dtype="float32"),1)
                with rasterio.open(f) as ds:
                    if resolution==0.5:
                        self.assertEqual(dt.check_tile(ds)["invalid_pixels"],0)
                    else:
                        with self.assertRaisesRegex(ValueError,"0.5 m"):
                            dt.check_tile(ds)

    def test_invalid_runtime_grid(self):
        t=synthetic_grid(5)
        self.assertEqual(t["source"],"SYNTHETIC TEST TERRAIN")
        self.assertAlmostEqual(height_at(t,13,7),0.212,places=3)
        for key,val in [("origin_lat_lon",[0,0]),("nx",2),("heights",[float("nan")])]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate({**t,key:val})

if __name__=="__main__":
    unittest.main()
