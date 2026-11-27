import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location("dgt_buildings",Path(__file__).resolve().parents[1]/"tools/build-dgt-buildings.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class BuildingHeightTests(unittest.TestCase):
    def test_constant_roof_on_sloping_ground(self):
        ground=np.ma.array(np.arange(100).reshape(10,10)*0.1)
        surface=ground+7.2
        inside=np.ones((10,10),dtype=bool)
        r=m.stats(ground,surface,inside)
        self.assertEqual(r["height_m"],7.2)
        self.assertTrue(r["interior_used"])
        self.assertEqual(r["quality"],"raster_candidate")
    def test_edges_and_nodata(self):
        ground=np.ma.array(np.zeros((12,12)),mask=False)
        surface=ground+6
        inside=np.ones((12,12),dtype=bool)
        surface.data[0,:]=50
        self.assertEqual(m.stats(ground,surface,inside)["height_m"],6)
        surface.mask[2:10,2:10]=True
        self.assertEqual(m.stats(ground,surface,inside)["reason"],"insufficient_coverage")
    def test_bad_difference_and_mixed_roofs(self):
        ground=np.ma.array(np.zeros((10,10)))
        inside=np.ones((10,10),dtype=bool)
        self.assertIsNone(m.stats(ground,ground-2,inside)["height_m"])
        surface=ground+3
        surface[:,5:]=15
        self.assertEqual(m.stats(ground,surface,inside)["reason"],"heterogeneous_surface_needs_lidar")
    def test_invalid_geometry(self):
        self.assertIsNone(m.geometry_of({"geometry":[{"lat":0,"lon":0}]}))
