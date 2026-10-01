"""Deterministic image-analysis checks using locally generated lossless images."""

import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from jsonschema import Draft7Validator

from tools.image_analyzer import analyze_image


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ImageAnalyzerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads(
            (PROJECT_ROOT / "schemas" / "photo_analysis_schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft7Validator.check_schema(schema)
        cls.validator = Draft7Validator(schema)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="colorist-analysis-test-", dir=PROJECT_ROOT
        )
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def analyze(self, pixels, filename="input.png"):
        path = self.directory / filename
        success, encoded = cv2.imencode(".png", pixels)
        self.assertTrue(success, "OpenCV must encode the synthetic test image")
        encoded.tofile(str(path))
        result = analyze_image(str(path))
        self.assertIsInstance(result, dict)
        self.validator.validate(result)
        self.assertEqual(json.loads(json.dumps(result)), result)
        for key in (
            "resolution", "brightness", "contrast", "exposure", "saturation",
            "dominant_colors", "metrics", "lighting", "technical", "color",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["lighting"]["contrast"], result["contrast"])
        self.assertEqual(result["technical"]["exposure"], result["exposure"])
        self.assertEqual(result["color"]["saturation"], result["saturation"])
        self.assertEqual(result["color"]["dominant_colors"], result["dominant_colors"])
        return result

    @staticmethod
    def solid_gray(value, width=80, height=60):
        return np.full((height, width, 3), value, dtype=np.uint8)

    @staticmethod
    def solid_hue(hue):
        hsv = np.full((60, 80, 3), (hue, 255, 255), dtype=np.uint8)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    def test_black_white_and_middle_gray(self):
        cases = (
            (0, "dark", "underexposed", "black"),
            (128, "balanced", "balanced", "gray"),
            (255, "bright", "overexposed", "white"),
        )
        for value, brightness, exposure, color in cases:
            with self.subTest(value=value):
                result = self.analyze(self.solid_gray(value))
                self.assertEqual(result["resolution"], {"width": 80, "height": 60})
                self.assertEqual(result["brightness"], brightness)
                self.assertEqual(result["exposure"], exposure)
                self.assertEqual(result["contrast"], "low")
                self.assertEqual(result["saturation"], "low")
                self.assertEqual(result["dominant_colors"], [color])
                self.assertAlmostEqual(result["metrics"]["mean_brightness"], value)
                self.assertAlmostEqual(result["metrics"]["grayscale_std"], 0)

    def test_balanced_binary_image_has_high_contrast(self):
        pixels = self.solid_gray(0, width=100, height=100)
        pixels[:, 50:] = 255
        result = self.analyze(pixels)
        self.assertEqual(result["brightness"], "balanced")
        self.assertEqual(result["contrast"], "high")
        self.assertEqual(result["exposure"], "balanced")
        self.assertEqual(set(result["dominant_colors"]), {"black", "white"})
        self.assertAlmostEqual(result["metrics"]["shadow_ratio"], 0.5)
        self.assertAlmostEqual(result["metrics"]["highlight_ratio"], 0.5)

    def test_exposure_detects_large_clipped_shadow_or_highlight(self):
        for clipped, expected in ((0, "underexposed"), (255, "overexposed")):
            with self.subTest(clipped=clipped):
                pixels = self.solid_gray(128, width=100, height=100)
                pixels[:, :40] = clipped
                result = self.analyze(pixels)
                self.assertEqual(result["exposure"], expected)

    def test_dark_without_clipping_keeps_exposure_balanced(self):
        result = self.analyze(self.solid_gray(32))
        self.assertEqual(result["brightness"], "dark")
        self.assertEqual(result["exposure"], "balanced")
        self.assertEqual(result["metrics"]["shadow_ratio"], 0)

    def test_red_wrap_green_and_blue_are_identified(self):
        for hue, color in ((0, "red"), (179, "red"), (60, "green"), (110, "blue")):
            with self.subTest(hue=hue):
                result = self.analyze(self.solid_hue(hue))
                self.assertEqual(result["dominant_colors"], [color])
                self.assertEqual(result["saturation"], "high")

    def test_neutral_image_has_no_spurious_red(self):
        pixels = self.solid_gray(128, width=100, height=100)
        pixels[:, :30] = 0
        pixels[:, 70:] = 255
        result = self.analyze(pixels)
        self.assertEqual(set(result["dominant_colors"]), {"black", "gray", "white"})
        self.assertNotIn("red", result["dominant_colors"])

    def test_small_color_patch_does_not_dominate_neutral_background(self):
        pixels = self.solid_gray(128, width=100, height=100)
        pixels[:, :1] = (0, 0, 255)
        result = self.analyze(pixels)
        self.assertEqual(result["dominant_colors"], ["gray"])

    def test_multiple_large_color_regions_return_three_colors(self):
        pixels = np.empty((100, 100, 3), dtype=np.uint8)
        pixels[:, :50] = (0, 255, 0)
        pixels[:, 50:80] = (255, 0, 0)
        pixels[:, 80:] = (0, 128, 255)
        result = self.analyze(pixels)
        self.assertEqual(result["dominant_colors"], ["green", "blue", "orange"])

    def test_large_image_preserves_dimensions_and_bounds_hsv_sample(self):
        pixels = self.solid_gray(128, width=1920, height=1280)
        pixels[:, :173] = 0
        result = self.analyze(pixels)
        self.assertEqual(result["resolution"], {"width": 1920, "height": 1280})
        sample = result["metrics"]["sample_resolution"]
        self.assertEqual(max(sample["width"], sample["height"]), 1024)
        self.assertAlmostEqual(sample["width"] / sample["height"], 1.5, delta=0.005)
        self.assertAlmostEqual(result["metrics"]["shadow_ratio"], 173 / 1920, places=4)
        self.assertAlmostEqual(
            result["metrics"]["mean_brightness"], 128 * (1920 - 173) / 1920,
            places=3,
        )

    def test_unicode_filename_is_supported(self):
        result = self.analyze(self.solid_gray(128), filename="摄影分析测试.png")
        self.assertEqual(result["brightness"], "balanced")

    def test_missing_image_raises_clear_error(self):
        with self.assertRaises(FileNotFoundError):
            analyze_image(str(self.directory / "missing.png"))

    def test_empty_or_invalid_image_raises_clear_error(self):
        for content in (b"", b"This is not an image."):
            with self.subTest(content=content):
                path = self.directory / "invalid.png"
                path.write_bytes(content)
                with self.assertRaises(ValueError):
                    analyze_image(str(path))

    def test_empty_path_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_image("")


if __name__ == "__main__":
    unittest.main()
