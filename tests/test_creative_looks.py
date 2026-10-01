"""Check distributable assets and perceptible behavior on independent images."""

import hashlib
import json
from pathlib import Path
import unittest
import importlib.util

import cv2
import numpy as np
from tools.lut_engine import load_cube, apply_simple_lut
from tools.look_library import list_looks

ROOT = Path(__file__).resolve().parents[1]


class CreativeLooksTests(unittest.TestCase):
    def test_example_recipes_reproduce_distributed_tables(self):
        spec = importlib.util.spec_from_file_location("example_baker", ROOT / "scripts/bake_example_luts.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        items = json.loads((ROOT / "examples/grades/recipes.json").read_text(encoding="utf-8"))["recipes"]
        self.assertEqual(len(items), 4)
        for item in items:
            with self.subTest(example=item["id"]):
                asset = ROOT / item["path"]
                self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), item["sha256"])
                np.testing.assert_allclose(module.bake(item), load_cube(asset)["table"], atol=6e-8, rtol=0)

    def test_public_fixtures_match_recorded_sources(self):
        sources = json.loads((ROOT / "tests/fixtures/sources.json").read_text(encoding="utf-8"))["sources"]
        self.assertEqual(len(sources), 4)
        for item in sources:
            with self.subTest(fixture=item["file"]):
                self.assertEqual(hashlib.sha256((ROOT / "tests/fixtures" / item["file"]).read_bytes()).hexdigest(), item["sha256"])

    def test_catalog_assets_have_valid_checksums_and_licenses(self):
        entries = list_looks()["looks"]
        self.assertEqual(len(entries), 18)
        self.assertEqual(len({e["id"] for e in entries}), 18)
        for e in entries:
            with self.subTest(look=e["id"]):
                self.assertEqual(hashlib.sha256((ROOT / e["path"]).read_bytes()).hexdigest(), e["sha256"])
                self.assertTrue((ROOT / e["license"]["license_path"]).is_file())
                self.assertTrue((ROOT / e["license"]["attribution_path"]).is_file())

    def test_original_looks_preserve_endpoints_and_neutral_gradient(self):
        ramp = np.repeat(np.arange(256, dtype=np.uint8)[None, :, None], 3, axis=2)
        for e in list_looks()["looks"]:
            if not e["id"].startswith("ac_"):
                continue
            with self.subTest(look=e["id"]):
                result = apply_simple_lut(ramp, load_cube(ROOT / e["path"]))
                np.testing.assert_array_equal(result[0, 0], [0, 0, 0])
                np.testing.assert_array_equal(result[0, -1], [255, 255, 255])
                gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)[0].astype(int)
                self.assertTrue(np.all(np.diff(gray) >= 0))
                self.assertGreater(len(np.unique(gray)), 210)

    def test_all_original_looks_change_independent_coffee_photo(self):
        image = cv2.imread(str(ROOT / "tests/fixtures/coffee.png"))
        self.assertIsNotNone(image)
        for e in list_looks()["looks"]:
            if not e["id"].startswith("ac_"):
                continue
            with self.subTest(look=e["id"]):
                result = apply_simple_lut(image, load_cube(ROOT / e["path"]))
                self.assertGreater(cv2.absdiff(result, image).mean(), 1)
                if e["id"] == "ac_silver_mono":
                    np.testing.assert_array_equal(result[:, :, 0], result[:, :, 1])
                    np.testing.assert_array_equal(result[:, :, 1], result[:, :, 2])
