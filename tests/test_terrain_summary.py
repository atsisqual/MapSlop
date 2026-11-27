import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("terrain_summary",Path(__file__).resolve().parents[1]/"tools/summarize-terrain-validation.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SummaryTest(unittest.TestCase):
    def test_both_required_and_choose_default(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            manifest={"products":[{"cell_m":cell,"vertices":vertices,"bytes":10,"sha256":"a"*64,
                       "error":{"points":100,"max_abs_m":0.9,"mean_abs_m":0.2,"rmse_m":0.3}}
                       for cell,vertices in [(2,250000),(5,41000)]],
                      "coverage":{"pixels_checked":100,"invalid_pixels":0},"inputs":[],
                      "source_release":"fixture","source_crs":"EPSG:3763"}
            for cell in (2,5):
                q=p/str(cell);q.mkdir()
                (q/"browser-report.json").write_text(json.dumps({"success":True,"distance":2.2,"multiTouch":True,"touchRelease":True,
                    "terrain":{"cell":cell,"source":"DGT MDT 0.5 m","contactSamples":5,
                    "contactDuringDrive":{"max":0.03,"mean":0.02},"collisionSurfaceDuringDrive":{"max":0.03}}}))
            result=mod.summarize(manifest,p)
            self.assertTrue(result["pass"])
            self.assertEqual(result["recommended_default_cell_m"],5)
            manifest["products"][1]["error"]["max_abs_m"]=1.01
            self.assertFalse(mod.summarize(manifest,p)["pass"])
            manifest["products"][1]["error"]["max_abs_m"]=0.9
            (p/"5"/"browser-report.json").unlink()
            self.assertIsNone(mod.summarize(manifest,p)["recommended_default_cell_m"])
