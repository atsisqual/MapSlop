import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("summarize_terrain",Path(__file__).resolve().parents[1]/"tools/summarize-terrain-validation.py")
st=importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

class ManifestTest(unittest.TestCase):
    def test_selection_contract(self):
        for kind,grid_ok,passed in [("tin",False,True),("grid",True,True),(None,False,False)]:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                p=Path(d)
                (p/"terrain-default.json").write_bytes(b"legacy")
                manifest={"schema":2,"grid_candidate_precision_pass":grid_ok,
                          "validation_status":"pending","final_pass":None,"default":None}
                report={"pass":passed,"recommended_default_file":None,"results":[],
                        "run_id":"123","tested_commit":"abc"}
                if passed:
                    name="terrain-tin.bin" if kind=="tin" else "terrain-2m.bin"
                    data=b"candidate"
                    (p/name).write_bytes(data)
                    report.update(recommended_default_file=name,results=[{
                        "file":name,"pass":True,"kind":kind,"cell_m":None if kind=="tin" else 2,
                        "sha256":hashlib.sha256(data).hexdigest(),"raw_bytes":len(data)}])
                final=st.finalize_manifest(manifest,report,p)
                self.assertEqual(final["grid_candidate_precision_pass"],grid_ok)
                self.assertEqual(final["final_pass"],passed)
                self.assertEqual(final["validation_status"],"passed" if passed else "failed")
                self.assertFalse((p/"terrain-default.json").exists())
                self.assertEqual((p/"terrain-default.bin").exists(),passed)
                if passed:
                    self.assertEqual((p/"terrain-default.bin").read_bytes(),data)
                    self.assertEqual(final["default"]["sha256"],hashlib.sha256(data).hexdigest())
                    self.assertEqual(final["default"]["file"],name)
                else:
                    self.assertIsNone(final["default"])

    def test_corrupt_selected_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"terrain-tin.bin").write_bytes(b"bad")
            (p/"terrain-default.bin").write_bytes(b"stale")
            with self.assertRaisesRegex(ValueError,"hash/size"):
                st.finalize_manifest({"schema":2},{"pass":True,
                    "recommended_default_file":"terrain-tin.bin","results":[{"file":"terrain-tin.bin",
                    "pass":True,"sha256":"wrong","raw_bytes":3}]},p)
            self.assertFalse((p/"terrain-default.bin").exists())
