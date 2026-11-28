import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from terrain_grid import ORIGIN,KX,KY
spec=importlib.util.spec_from_file_location("combined",Path(sys.path[0])/"install-combined-preview.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class CombinedTests(unittest.TestCase):
    def test_sides(self):
        self.assertEqual(m.sides({}),{})
        self.assertEqual(m.sides({"sidewalk":"no"}),{})
        self.assertEqual(m.sides({"sidewalk":"separate"}),{})
        self.assertEqual(m.sides({"sidewalk":"left"}),{"left":1.5})
        self.assertEqual(m.sides({"sidewalk":"both","sidewalk:right":"separate","sidewalk:left:width":"2.2 m"}),{"left":2.2})
        self.assertEqual(m.sides({"sidewalk":"both","sidewalk:width":"100"}),{"left":1.5,"right":1.5})
    def test_paving(self):
        g=[{"lon":ORIGIN[1]+x/KX,"lat":ORIGIN[0]-z/KY} for x,z in [(0,0),(4,0),(4,4),(0,4),(0,0)]]
        rows=[{"type":"way","id":i,"tags":t,"geometry":g} for i,t in enumerate([
            {"highway":"residential"},{"highway":"footway","surface":"dirt"},
            {"highway":"footway","footway":"sidewalk","width":"1.8"},
            {"highway":"pedestrian","area":"yes","surface":"sett"},
            {"building":"church","surface":"sett"},{"landuse":"grass","area":"yes"},
            {"amenity":"parking","surface":"asphalt"}],1)]
        p=m.paving({"elements":rows})
        self.assertEqual(p["sidewalks"],{})
        self.assertEqual(p["paths"],{"3":1.8})
        self.assertEqual({v["id"] for v in p["areas"]},{"4","7"})
    def test_roof_sampling_ignores_edges(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            rgb=np.full((48,48,3),[170,80,45],dtype=np.uint8)
            rgb[4:44,25:44]=[140,140,140]
            Image.fromarray(rgb).save(p/"near.webp",lossless=True)
            (p/"manifest.json").write_text(json.dumps({"world_extent":[0,0,12,12],"tile_m":12,"gutter_m":0,"tiles":[{"i":0,"j":0,"levels":{"near":{"path":"near.webp","px":48,"metres_per_pixel":0.25}}}]}))
            geo={"buildings":[{"id":1,"ring":[1,1,5,1,5,10,1,10]},{"id":2,"ring":[7,1,10,1,10,10,7,10]}]}
            result=m.roof_colors(geo,p)
            self.assertEqual(result["1"]["class"],"terracotta")
            self.assertEqual(result["2"]["class"],"gray")
            self.assertEqual(result["1"]["inner_margin_m"],.75)
            self.assertGreater(result["1"]["samples"],4)
if __name__=="__main__":unittest.main()
