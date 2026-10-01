"""Bake original, source-independent creative CUBE33 looks; never read a photo.

Fixed analytic Lab tone/color transforms are authored recipes, not pretrained
weights or photographer LUTs. Runtime grading still uses tools.lut_engine.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.lut_engine import apply_simple_lut, load_cube

SIZE = 33
LOOKS = [
    # id, name, contrast, midtone lift, chroma, rotation, shadow a/b, highlight a/b, scenes
    ("amber_dusk", "Amber Dusk", .20, .00, 1.12, 0, [0, -4], [3, 9], ["golden hour", "warm travel"]),
    ("coral_dusk", "Coral Dusk", .18, .00, 1.10, -3, [1, -3], [8, 4], ["sunset", "coral warm light"]),
    ("teal_gold", "Teal Gold", .24, .00, 1.16, 0, [-9, -7], [0, 9], ["city sunset", "bold travel"]),
    ("vivid_travel", "Vivid Travel", .30, .02, 1.24, 0, [-2, -3], [2, 5], ["travel", "landscape"]),
    ("clean_landscape", "Clean Landscape", .18, .01, 1.08, 0, [-2, -2], [0, 2], ["landscape", "daylight"]),
    ("olive_gold", "Olive Gold", .20, .00, 1.10, 5, [-4, 4], [-2, 8], ["graphic landscape", "architecture"]),
    ("urban_cool", "Urban Cool", .26, -.01, 1.05, 0, [-4, -7], [-1, -2], ["urban blue hour", "night"]),
    ("soft_editorial", "Soft Editorial", -.12, .02, .94, 0, [1, -2], [2, 3], ["portrait preview", "soft daylight"]),
    ("neutral_density", "Neutral Density", .30, -.01, 1.02, 0, [0, 0], [0, 0], ["documentary", "strong neutral tone"]),
    ("silver_mono", "Silver Mono", .32, .00, 0., 0, [0, 0], [0, 0], ["black-and-white", "shape and texture"]),
]


def linear_rgb(lab):
    fy = (lab[:, 0] + 16) / 116
    xyz = np.column_stack((fy + lab[:, 1] / 500, fy, fy - lab[:, 2] / 200))
    delta = 6 / 29
    xyz = np.where(xyz > delta, xyz ** 3, 3 * delta ** 2 * (xyz - 4 / 29))
    xyz *= [0.950456, 1.0, 1.088754]
    return xyz @ np.array([[3.240479, -1.537150, -.498535],
                           [-.969256, 1.875991, .041556],
                           [.055648, -.204043, 1.057311]]).T


def encode_gamut(lab):
    """Reduce chroma at fixed L* for out-of-gamut nodes instead of channel clipping."""
    linear = linear_rgb(lab)
    outside = np.any((linear < 0) | (linear > 1), axis=1)
    values = lab[outside].copy()
    ab = values[:, 1:].copy()
    low, high = np.zeros(len(values)), np.ones(len(values))
    for _ in range(20):
        factor = (low + high) / 2
        values[:, 1:] = ab * factor[:, None]
        probe = linear_rgb(values)
        valid = np.all((probe >= 0) & (probe <= 1), axis=1)
        low, high = np.where(valid, factor, low), np.where(valid, high, factor)
    values[:, 1:] = ab * low[:, None]
    linear[outside] = linear_rgb(values)
    linear = np.clip(linear, 0, 1)
    return np.where(linear <= .0031308, 12.92 * linear,
                    1.055 * linear ** (1 / 2.4) - .055)


def bake(recipe):
    _, _, contrast, lift, saturation, degrees, shadows, highlights, _ = recipe
    blue, green, red = np.indices((SIZE,) * 3, dtype=np.float32)
    rgb = np.stack((red, green, blue), axis=-1).reshape(-1, 3) / (SIZE - 1)
    lab = cv2.cvtColor(rgb.reshape(1, -1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3).astype(np.float64)
    x = lab[:, 0] / 100
    lab[:, 0] = 100 * (x + contrast * x * (1-x) * (2*x-1) + lift * np.sin(np.pi*x)**2)
    chroma = np.linalg.norm(lab[:, 1:], axis=1)
    hue = np.arctan2(lab[:, 2], lab[:, 1])
    # Broad continuous orange-hue attenuation only. This does not detect people.
    distance = np.arctan2(np.sin(hue - .85), np.cos(hue - .85))
    orange_guard = np.exp(-.5*(distance/.36)**2) * (1-np.exp(-chroma/8))
    attenuation = 1 - .75 * orange_guard
    angle = np.deg2rad(degrees) * attenuation
    a, b = lab[:, 1].copy(), lab[:, 2].copy()
    lab[:, 1] = a*np.cos(angle)-b*np.sin(angle)
    lab[:, 2] = a*np.sin(angle)+b*np.cos(angle)
    if saturation == 0:
        lab[:, 1:] = 0
    else:
        lab[:, 1:] *= (1 + (saturation-1)*attenuation)[:, None]
        tint = (1-x)[:, None]*np.asarray(shadows) + x[:, None]*np.asarray(highlights)
        tint *= (np.sin(np.pi*x)**1.3 * attenuation * (.25+.75*(1-np.exp(-chroma/12))))[:, None]
        lab[:, 1:] += tint
    result = encode_gamut(lab)
    if saturation == 0:
        # Force exact neutral RGB despite rounded XYZ matrices.
        result[:] = result.mean(axis=1, keepdims=True)
    result[0], result[-1] = 0, 1
    return result


def build():
    directory = ROOT / "assets/luts/creative-v1"
    directory.mkdir(parents=True, exist_ok=True)
    catalog_path = ROOT / "assets/luts/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["luts"] = [item for item in catalog["luts"] if not item["id"].startswith("ac_")]
    catalog["collections"] = [c for c in catalog["collections"] if c["id"] != "creative-v1"]
    catalog.pop("learned_source_conditioned_catalog", None)
    catalog["collections"].append({"id": "creative-v1", "license": "MIT", "count": 10})
    for recipe in LOOKS:
        slug, name, contrast, lift, chroma, degrees, shadows, highlights, scenes = recipe
        path = directory / f"{slug}.cube"
        with path.open("w", encoding="ascii", newline="\n") as stream:
            stream.write(f'# AI Colorist original analytic look; MIT; no training or source photograph.\n'
                         f'# Encoded sRGB input/output; global color mapping, no spatial effects.\n'
                         f'TITLE "AI Colorist {name}"\nLUT_3D_SIZE {SIZE}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
            np.savetxt(stream, bake(recipe), fmt="%.9f")
        lut = load_cube(path)
        ramp = np.repeat(np.arange(256, dtype=np.uint8)[None, :, None], 3, axis=2)
        mapped = apply_simple_lut(ramp, lut)
        gray = cv2.cvtColor(mapped, cv2.COLOR_BGR2GRAY)
        if np.any(np.diff(gray.astype(float)) < 0):
            raise ValueError(f"Nonmonotonic gray ramp: {name}")
        entry = {
            "id": f"ac_{slug}", "name": f"AI Colorist {name}", "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source": {"author": "FantasyChino and AI Colorist contributors (AI-assisted analytic design)",
                       "url": "https://github.com/FantasyChino/ai-colorist-agent",
                       "modifications": "Original fixed analytic recipe; no photographer LUT values, corpus or source-image fit."},
            "license": {"spdx": "MIT", "license_path": "LICENSE",
                        "attribution_path": "assets/luts/creative-v1/ATTRIBUTION.md"},
            "color_space": {"input": "display-referred encoded sRGB RGB [0,1]",
                            "output": "display-referred encoded sRGB RGB [0,1]",
                            "status": "design_declared_not_icc_conversion"},
            "source_dependent": False,
            "usage": {"scenes": scenes, "avoid": ["color-critical products", "unconverted RAW/Log/HDR/P3"],
                      "initial_strength_range": [1., 1.] if chroma == 0 else [.5, .85],
                      "auto_select": False, "limitations": ["Global LUT; inspect important colors and highlight gradients.",
                       "Orange-hue attenuation is not semantic skin protection.", "Cannot recover clipped detail or encode dehazing/masks."]},
            "recipe": {"contrast": contrast, "midtone_lift": lift, "chroma_scale": chroma,
                       "hue_degrees": degrees, "shadow_lab_ab": shadows, "highlight_lab_ab": highlights},
            "validation": {"size": SIZE, "rows": SIZE**3, "finite_unit_range": bool(np.isfinite(lut["table"]).all()
                and lut["table"].min() >= 0 and lut["table"].max() <= 1),
                "gray_ramp_decreasing_steps_8bit": int(np.count_nonzero(np.diff(gray.astype(float)) < 0)),
                "black_rgb": lut["table"][0].tolist(), "white_rgb": lut["table"][-1].tolist()}
        }
        catalog["luts"].append(entry)
    catalog["version"] = 2
    catalog["purpose"] = "Ten ready-to-use original creative looks plus eight separately licensed third-party candidates. No user training required."
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"original_looks": 10, "total_luts": len(catalog["luts"]), "requires_training": False}))


if __name__ == "__main__":
    build()
