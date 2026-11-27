import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("dgt_workflow", Path(__file__).resolve().parents[1] / "tools/dgt-workflow.py")
dgt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dgt)

class TestPlan(unittest.TestCase):
    def test_all_modes(self):
        for mode in dgt.MODES:
            with self.subTest(mode=mode):
                cmd, tag = dgt.plan(mode, "MDS-50cm", "20261127", "/tmp/out")
                self.assertIn("--output", cmd)
                if mode.startswith("pilot-"):
                    self.assertIsNone(tag)
                    self.assertEqual("--login" in cmd, mode == "pilot-authenticated")
                else:
                    self.assertEqual(tag, ("geodata-dgt-history-" if mode == "historical" else "geodata-dgt-pedome-") + "20261127")
                if mode == "laz":
                    self.assertEqual(cmd[-2:], ["--collection", "LAZ"])
                if mode == "collection":
                    self.assertEqual(cmd[-2:], ["--collection", "MDS-50cm"])
                if mode == "historical":
                    self.assertIn("--historical-orthos", cmd)

    def test_invalid_inputs(self):
        for args in [("bad","MDT-50cm","20261127"),("collection","bad","20261127"),
                     ("expanded","MDT-50cm","20260230"),("expanded","MDT-50cm","x; echo bad")]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                dgt.plan(*args, "/tmp/out")

class TestArchive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.name = "LO-test.laz"
        self.payload = b"LASF" + b"fixture"
        (self.path / self.name).write_bytes(self.payload)
        self.item = {"ok": True, "filename": self.name, "bytes": len(self.payload),
                     "sha256": hashlib.sha256(self.payload).hexdigest()}

    def manifest(self, *items):
        (self.path / "manifest.json").write_text(json.dumps({"items": items}))

    def test_partial_verified(self):
        self.manifest(self.item, {"ok": False, "error": "fixture"})
        files = dgt.verified_files(self.path)
        self.assertEqual(list(files), [self.name])
        fp = files[self.name]
        existing = {"name": self.name, "size": fp["bytes"], "digest": "sha256:" + fp["sha256"]}
        self.assertTrue(dgt.same_asset(existing, fp))
        self.assertFalse(dgt.same_asset({**existing, "digest": "sha256:" + "0"*64}, fp))

    def test_corruption(self):
        self.manifest({**self.item, "sha256": "0"*64})
        with self.assertRaises(ValueError):
            dgt.verified_files(self.path)

    def test_unsafe_duplicate_empty(self):
        for items in [({**self.item, "filename": "../escape.laz"},), (self.item, self.item), ({"ok": False},)]:
            with self.subTest(items=items):
                self.manifest(*items)
                with self.assertRaises(ValueError):
                    dgt.verified_files(self.path)

    def test_bad_signature(self):
        (self.path / self.name).write_bytes(b"HTML")
        self.manifest(self.item)
        with self.assertRaises(ValueError):
            dgt.verified_files(self.path)

if __name__ == "__main__":
    unittest.main()
