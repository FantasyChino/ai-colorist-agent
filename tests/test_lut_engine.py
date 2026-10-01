import tempfile
import unittest
from pathlib import Path

import numpy as np

from tools.lut_engine import apply_simple_lut, load_cube


def identity(size=2):
    levels = np.linspace(0, 1, size)
    return {"size": size, "table": np.array([
        [r, g, b] for b in levels for g in levels for r in levels
    ], dtype=np.float32)}


class CubeLutTests(unittest.TestCase):
    def test_identity_preserves_rgb_primaries_and_all_gray_values(self):
        primaries = np.array([[[0, 0, 255], [0, 255, 0], [255, 0, 0]]], dtype=np.uint8)
        ramp = np.repeat(np.arange(256, dtype=np.uint8)[None, :, None], 3, axis=2)
        for size in (2, 5, 17):
            np.testing.assert_array_equal(apply_simple_lut(primaries, identity(size)), primaries)
            np.testing.assert_array_equal(apply_simple_lut(ramp, identity(size)), ramp)

    def test_identity_preserves_random_colors_across_processing_chunks(self):
        image = np.random.default_rng(42).integers(0, 256, (257, 257, 3), dtype=np.uint8)
        np.testing.assert_array_equal(apply_simple_lut(image, identity(5)), image)

    def test_affine_color_transform_interpolates_between_grid_points(self):
        lut = identity()
        lut["table"] = lut["table"] @ np.array([
            [0.8, 0.0, 0.0], [0.2, 1.0, 0.0], [0.0, 0.0, 0.6]
        ], dtype=np.float32)
        image = np.array([[[120, 64, 192]]], dtype=np.uint8)
        expected = np.array([[[72, 64, 166]]], dtype=np.uint8)
        np.testing.assert_array_equal(apply_simple_lut(image, lut), expected)

    def test_cube_loads_utf8_comments_and_domains(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            path = Path(temporary) / "恒等.cube"
            rows = "\n".join(" ".join(map(str, row)) for row in identity()["table"])
            path.write_text('TITLE "Identity"\nLUT_3D_SIZE 2\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 0.5 0.5 0.5\n' + rows + " # final row\n", encoding="utf-8")
            lut = load_cube(path)
            image = np.full((1, 1, 3), 64, dtype=np.uint8)
            np.testing.assert_array_equal(apply_simple_lut(image, lut), np.full_like(image, 128))

    def test_malformed_cubes_fail_instead_of_silent_black_pixels(self):
        for text in (
            "LUT_3D_SIZE 2\n0 0 0\n",
            "LUT_1D_SIZE 2\n0 0 0\n1 1 1\n",
            "LUT_3D_SIZE 1\n0 0 0\n",
            "LUT_3D_SIZE 2\nDOMAIN_MAX 0 0 0\n" + "0 0 0\n" * 8,
            "LUT_3D_SIZE 2\n" + "nan 0 0\n" * 8,
        ):
            with self.subTest(text=text[:40]), tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
                path = Path(temporary) / "invalid.cube"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_cube(path)


if __name__ == "__main__":
    unittest.main()
