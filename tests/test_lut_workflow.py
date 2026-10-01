"""Regression checks for creative strength and licensed derived assets."""

import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

import numpy as np

from tools.lut_engine import apply_simple_lut, load_cube

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_lut", ROOT / "skills/color-strategy/scripts/prepare_lut.py")
WORKFLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKFLOW)
sys.path.insert(0, str(ROOT / "skills/color-strategy/scripts"))
from preview_luts import preview


class LutWorkflowTests(unittest.TestCase):
    def test_strength_endpoints_and_encoded_rgb_blend(self):
        entry = WORKFLOW.catalog_entries()["pat_fuji_velvia_50"]
        image = np.random.default_rng(8).integers(0, 256, (90, 70, 3), dtype=np.uint8)
        identity = apply_simple_lut(image, WORKFLOW.mixed_lut(entry, 0))
        np.testing.assert_array_equal(identity, image)
        source = apply_simple_lut(image, load_cube(ROOT / entry["path"]))
        full = apply_simple_lut(image, WORKFLOW.mixed_lut(entry, 1))
        np.testing.assert_array_equal(full, source)
        partial = apply_simple_lut(image, WORKFLOW.mixed_lut(entry, 0.25))
        rounded_blend = np.rint(image.astype(float) * 0.75 + source.astype(float) * 0.25)
        self.assertLessEqual(np.max(np.abs(partial.astype(float) - rounded_blend)), 1)

    def test_derived_cube_preserves_license_and_provenance(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as folder:
            path = Path(folder) / "派生.cube"
            result = WORKFLOW.prepare_lut("pat_kodak_portra_160", 0.2, path)
            lut = load_cube(result["lut_path"])
            self.assertEqual(lut["size"], 33)
            provenance = json.loads(Path(result["provenance_path"]).read_text(encoding="utf-8"))
            self.assertEqual(provenance["license"], "CC-BY-SA-4.0")
            self.assertEqual(provenance["strength"], 0.2)
            entry = WORKFLOW.catalog_entries()[provenance["source_id"]]
            self.assertEqual(Path(provenance["license_path"]).read_bytes(), (ROOT / entry["license"]["license_path"]).read_bytes())
            notice = Path(provenance["attribution_path"]).read_text(encoding="utf-8")
            self.assertIn("identity blend at strength 0.2", notice)
            self.assertIn("upstream notice below describes the original", notice)
            self.assertTrue(notice.endswith((ROOT / entry["license"]["attribution_path"]).read_text(encoding="utf-8")))

    def test_preview_rejects_input_collision_with_derived_assets(self):
        # Decode-by-content means a valid PNG can be named with any extension.
        import cv2
        from unittest.mock import patch

        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as folder:
            source = Path(folder) / "strength-0.250000.cube"
            ok, encoded = cv2.imencode(".png", np.full((16, 16, 3), 128, dtype=np.uint8))
            self.assertTrue(ok)
            before = encoded.tobytes()
            source.write_bytes(before)
            with patch("preview_luts.default_output", return_value=source):
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    preview(source, ["lumix_meridian"], output_dir=Path(folder) / "preview")
            self.assertEqual(source.read_bytes(), before)

    def test_invalid_strength_checksum_and_source_overwrite_rejected(self):
        entry = WORKFLOW.catalog_entries()["lumix_meridian"]
        for amount in (-0.1, 1.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                WORKFLOW.mixed_lut(entry, amount)
        with self.assertRaisesRegex(ValueError, "checksum"):
            WORKFLOW.mixed_lut({**entry, "sha256": "wrong"}, 0.25)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            WORKFLOW.prepare_lut(entry["id"], 0.25, entry["path"])


if __name__ == "__main__":
    unittest.main()
