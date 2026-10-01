"""Verify real data sensitivity, exact identity, corpus counts and input safety."""

from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from tools import style_lut_learner as learner
from tools.lut_engine import apply_simple_lut, load_cube


def save_png(path, image):
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Could not create test image")
    encoded.tofile(path)


def make_references(directory, color, count=500, monochrome=False):
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        rng = np.random.default_rng(1700 + index)
        if monochrome:
            channel = rng.integers(30, 225, (12, 12, 1), dtype=np.uint8)
            image = np.repeat(channel, 3, axis=2)
        else:
            noise = rng.integers(-20, 21, (12, 12, 3))
            image = np.clip(np.asarray(color)[None, None, :] + noise, 0, 255).astype(np.uint8)
        save_png(directory / f"work-{index:04d}.png", image)


class StyleLutLearnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory()
        # Windows hosted runners can return an 8.3 alias for TEMP. Compare the
        # same canonical path representation as the production output resolver.
        cls.root = Path(cls.workspace.name).resolve()
        cls.source = cls.root / "source.png"
        yy, xx = np.indices((32, 32))
        image = np.stack((xx * 8, yy * 8, (xx + yy) * 4), axis=-1).astype(np.uint8)
        save_png(cls.source, image)
        cls.source_image = image
        cls.warm = cls.root / "warm"
        cls.cool = cls.root / "cool"
        cls.mono = cls.root / "monochrome"
        make_references(cls.warm, [40, 70, 145])
        make_references(cls.cool, [140, 90, 40])
        make_references(cls.mono, None, monochrome=True)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def fit(self, directory, name, strength=1.0):
        with patch.object(learner, "PROJECT_ROOT", self.root):
            return learner.learn_style_lut(str(self.source), str(directory), name, strength)

    def test_corpus_changes_fitted_parameters_and_lut(self):
        warm = self.fit(self.warm, "warm-data")
        cool = self.fit(self.cool, "cool-data")
        warm_profile = json.loads(Path(warm["profile_path"]).read_text(encoding="utf-8"))
        cool_profile = json.loads(Path(cool["profile_path"]).read_text(encoding="utf-8"))
        warm_ab = np.array(warm_profile["target_statistics"]["ab_means"])
        cool_ab = np.array(cool_profile["target_statistics"]["ab_means"])
        self.assertGreater(float((warm_ab[:, 1] - cool_ab[:, 1]).mean()), 20)
        warm_table = load_cube(warm["lut_path"])["table"]
        cool_table = load_cube(cool["lut_path"])["table"]
        self.assertGreater(float(np.mean(np.abs(warm_table - cool_table))), 0.025)
        self.assertTrue(warm["source_dependent"])
        self.assertEqual(warm["reference_count"], 500)
        self.assertEqual(warm["selected_reference_count"], 50)
        self.assertEqual(warm["counts"]["rejected"], 0)

    def test_strength_zero_is_exact_identity_with_red_fastest_order(self):
        result = self.fit(self.warm, "identity", strength=0)
        lut = load_cube(result["lut_path"])
        random_colors = np.random.default_rng(77).integers(0, 256, (31, 43, 3), dtype=np.uint8)
        np.testing.assert_array_equal(apply_simple_lut(random_colors, lut), random_colors)
        self.assertEqual(lut["size"], 33)
        self.assertEqual(lut["table"].shape, (35937, 3))
        np.testing.assert_array_equal(lut["table"][1], [1 / 32, 0, 0])
        np.testing.assert_array_equal(lut["table"][33], [0, 1 / 32, 0])

    def test_monochrome_references_are_included_and_fit_monochrome(self):
        result = self.fit(self.mono, "black-and-white")
        self.assertEqual(result["reference_count"], 500)
        self.assertEqual(result["selected_reference_count"], 50)
        self.assertEqual(result["color_image_ratio"], 0)
        self.assertEqual(result["counts"]["monochrome_like_images"], 500)
        lut = load_cube(result["lut_path"])
        output = apply_simple_lut(self.source_image, lut)
        self.assertLessEqual(int(np.max(np.ptp(output.astype(np.int32), axis=2))), 1)

    def test_inputs_survive_and_output_has_fitted_provenance(self):
        paths = [self.source, *sorted(self.warm.glob("*.png"))]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        first = self.fit(self.warm, "protected-inputs", strength=1.6)
        second = self.fit(self.warm, "protected-inputs", strength=1.6)
        self.assertEqual(first["lut_sha256"], second["lut_sha256"])
        for path, digest in before.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        manifest = json.loads(Path(first["manifest_path"]).read_text(encoding="utf-8"))
        profile = json.loads(Path(first["profile_path"]).read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["accepted"]), 500)
        self.assertEqual(profile["source"]["sha256"], before[self.source])
        self.assertIn("unpaired", profile["method"])
        self.assertIn("fitted_mapping", profile)
        self.assertEqual(profile["qc"]["neutral_ramp_lstar_decreasing_steps_over_0_025"], 0)
        self.assertTrue(Path(first["lut_path"]).is_relative_to(self.root / "assets/luts/learned"))

    def test_duplicates_bad_images_and_source_do_not_pad_minimum(self):
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            references = Path(directory)
            (references / "one.png").write_bytes((self.warm / "work-0000.png").read_bytes())
            (references / "copy.png").write_bytes((self.warm / "work-0000.png").read_bytes())
            (references / "source-copy.png").write_bytes(self.source.read_bytes())
            (references / "broken.png").write_bytes(b"invalid PNG")
            with self.assertRaises(learner.ReferenceSetError) as raised:
                self.fit(references, "insufficient")
            counts = raised.exception.details
            self.assertEqual(counts["candidates"], 4)
            self.assertEqual(counts["accepted"], 1)
            self.assertEqual(counts["rejected"], 3)
            self.assertEqual(counts["reject_summary"]["duplicate_file_sha256"], 1)
            self.assertEqual(counts["reject_summary"]["reference_matches_source_image"], 1)
            self.assertFalse((self.root / "assets/luts/learned/insufficient").exists())

    def test_invalid_strength_and_write_collision_are_rejected(self):
        for strength in (-0.1, 2.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.fit(self.warm, "invalid-strength", strength)
        with patch.object(learner, "PROJECT_ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "overwrite"):
                learner._guard_write_plan([self.source], [self.source])

    def test_repeated_luminance_quantiles_are_collapsed_without_rank_jump(self):
        axis, ranks = learner._collapse_quantile_ranks(np.full(len(learner.QUANTILES), 50.0))
        np.testing.assert_array_equal(axis, [50.0])
        np.testing.assert_allclose(ranks, [0.5], atol=1e-12)
        sampled = np.interp([49.999, 50.0, 50.001], axis, ranks)
        np.testing.assert_allclose(sampled, [0.5, 0.5, 0.5], atol=1e-12)

    def test_style_names_with_same_slug_do_not_overwrite_each_other(self):
        first = self.fit(self.warm, "A B")
        second = self.fit(self.warm, "a-b")
        self.assertNotEqual(first["profile_path"], second["profile_path"])
        first_profile = json.loads(Path(first["profile_path"]).read_text(encoding="utf-8"))
        second_profile = json.loads(Path(second["profile_path"]).read_text(encoding="utf-8"))
        self.assertEqual(first_profile["style_name"], "A B")
        self.assertEqual(second_profile["style_name"], "a-b")
        self.assertIn("runtime_versions", first_profile)

    def test_reference_tone_uses_source_percentile_anchors(self):
        source_stats = learner._image_statistics(self.source_image)
        reference_image = np.full((64, 64, 3), 120, dtype=np.uint8)
        reference_image[:, :32] = 20
        reference_image[:, 32:] = 235
        target_stats = learner._image_statistics(reference_image)
        target = {
            "normalized_luma_quantiles": target_stats["normalized_luma_quantiles"],
            "ab_means": target_stats["ab_means"],
            "ab_covariances": target_stats["ab_covariances"],
            "monochrome_like": target_stats["color_like"] is False,
        }
        mapping = learner._fit_mapping(source_stats, target)
        low, high = source_stats["luma_quantiles"][[0, -1]]
        mapped = np.interp([low, high], mapping["luma_axis"], mapping["luma_curve"])
        np.testing.assert_allclose(mapped, [low, high], atol=1.0)

    def test_monochrome_dominant_corpus_does_not_select_color_outliers(self):
        mono = learner._image_statistics(np.full((24, 24, 3), 110, dtype=np.uint8))
        color = learner._image_statistics(
            np.full((24, 24, 3), [20, 80, 210], dtype=np.uint8)
        )
        source = learner._image_statistics(self.source_image)
        selected, details = learner._select_creative_mode([mono] * 350 + [color] * 150, source)
        self.assertEqual(len(selected), 50)
        self.assertTrue(all(index < 350 for index in selected))
        self.assertIn("monochrome_dominant", details["method"])


if __name__ == "__main__":
    unittest.main()
