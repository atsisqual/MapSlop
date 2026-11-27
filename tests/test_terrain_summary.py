import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("terrain_summary",Path(__file__).resolve().parents[1]/"tools/summarize-terrain-validation.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SummaryTest(unittest.TestCase):
    def test_tin_then_fallback_and_distant_nonblocking(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            products=[]
            for kind,cell,v,label in [("grid",2,252506,"2"),("grid",5,41006,"5"),("grid",10,10404,"10"),("tin",None,50000,"tin")]:
                p={"kind":kind,"cell_m":cell,"file":"terrain-"+label+".json","vertices":v,"triangles":v*2,"bytes":10,"sha256":"a"*64,
                    "error":{"points":100,"max_abs_m":0.4 if kind=="tin" else 0.9,"mean_abs_m":0.2,"rmse_m":0.3},
                    "roads":{"points":1000,"ways":10,"max_abs_m":0.45,"mean_abs_m":0.1,"rmse_m":0.2}}
                if kind=="tin":p.update(library_error_m=0.25,target_error_m=0.25)
                products.append(p)
                q=path/label;q.mkdir()
                b={"success":True,"multiTouch":True,"touchRelease":True,
                    "terrain":{"kind":kind,"cell":cell,"source":"DGT MDT 0.5 m"},
                    "longDrive":{"success":True,"distance_m":106,"progress_m":104,"sample_count":1200,"contact_max_m":0.03,
                    "contact_mean_m":0.03,"surface_contact_max_m":0,"road_grade_20m":0.03,
                    "driven_heading_range_degrees":20,"collisions":0,"route":{"way":1,"name":"Fixture"}}}
                (q/"browser-report.json").write_text(json.dumps(b))
            manifest={"products":products,"coverage":{"pixels_checked":100,"invalid_pixels":0},"inputs":[],
                      "source_release":"fixture","source_crs":"EPSG:3763"}
            self.assertEqual(mod.summarize(manifest,path)["recommended_default_kind"],"tin")
            products[-1]["roads"]["max_abs_m"]=0.51
            products[1]["error"]["rmse_m"]=0.4
            r=mod.summarize(manifest,path)
            self.assertTrue(r["pass"])
            self.assertEqual(r["recommended_default_cell_m"],2)
            self.assertFalse(r["results"][1]["pass"])
            products[-1]["roads"]["max_abs_m"]=0.45
            products[-1]["vertices"]=150000
            self.assertEqual(mod.summarize(manifest,path)["recommended_default_cell_m"],2)
            (path/"2"/"browser-report.json").unlink()
            self.assertFalse(mod.summarize(manifest,path)["pass"])
