import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("preview",Path(__file__).resolve().parents[1]/"tools/verify-building-preview.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PreviewTests(unittest.TestCase):
    def test_normalized_ids_and_diagnostics(self):
        geo={"buildings":[{"id":f"way/{i}","h":6.25} for i in range(1,528)]}
        report={"building_count":527,"rows":[{"osm_id":1,"height_m":6.25,"preview_policy":"raster_p90_candidate"},
                 {"osm_id":"2","height_m":6.25,"preview_policy":"raster_p90_candidate"}]}
        r=m.compare(report,geo)
        self.assertTrue(r["pass"])
        self.assertEqual(r["matched"],2)
        geo["buildings"][0]["h"]=7
        r=m.compare(report,geo)
        self.assertFalse(r["pass"])
        self.assertEqual(r["mismatch_count"],1)
        geo["buildings"][0]["id"]="way/999"
        r=m.compare(report,geo)
        self.assertEqual(r["missing_ids"],[1])
    def test_reject_wrong_osm_type(self):
        with self.assertRaises(ValueError):m.osm_way_id("relation/12")

    def test_outline_exclusion_requires_exported_part(self):
        geo={"buildings":[{"id":i,"h":6.25} for i in range(1,527)]+[{"id":1531621904,"part":1,"h":3}]}
        report={"building_count":527,"rows":[{"osm_id":1493951967,"height_m":6.25,"preview_policy":"raster_p90_candidate"},{"osm_id":1,"height_m":6.25,"preview_policy":"raster_p90_candidate"}]}
        osm={"elements":[{"type":"way","id":1493951967,"nodes":[1,2,3,1],"tags":{"building":"roof","layer":"1"}},{"type":"way","id":1531621904,"nodes":[1,2,4,1],"tags":{"building:part":"yes"}}]}
        out=m.compare(report,geo,osm)
        self.assertTrue(out["pass"])
        self.assertEqual(out["excluded"][0]["replacement_osm_id"],1531621904)
        geo["buildings"][-1].pop("part")
        self.assertFalse(m.compare(report,geo,osm)["pass"])
