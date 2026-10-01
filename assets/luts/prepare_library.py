"""Convert selected Hald tables to CUBE and write measured provenance metadata.

This operates on LUT assets only, never on photographs. No upstream code runs.
Regeneration is offline after download_sources.py. It preserves the PNG originals.
"""

from pathlib import Path
import hashlib
import json
import struct

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
PAT_COMMIT = "af7b50d4caf6244fb6895a647f5b6a84efe7931a"
LUMIX_COMMIT = "708f98d97a26b123128480050c2a1459c8a58cca"
PAT_DIR = "pat-david-cc-by-sa-4.0"
MIT_DIR = "lumix-original-mit"

PAT_LOOKS = [
    ("kodak_portra_160", "negative_new", "Pat David Portra 160 approximation", ["portrait", "daylight", "travel"], ["strict product color accuracy", "already faded blacks"], [0.15, 0.35]),
    ("kodak_portra_400", "negative_new", "Pat David Portra 400 approximation", ["street", "documentary", "portrait"], ["bright high-key with delicate whites", "strict color accuracy"], [0.15, 0.35]),
    ("fuji_provia_100f", "colorslide", "Pat David Provia 100F approximation", ["daylight", "travel", "landscape"], ["already harsh contrast", "clipped saturated highlights"], [0.10, 0.30]),
    ("fuji_velvia_50", "colorslide", "Pat David Velvia 50 approximation", ["foliage", "landscape", "nature"], ["portrait skin", "neon or already saturated sunset", "strict color accuracy"], [0.10, 0.25]),
    ("fuji_superia_800", "negative_old", "Pat David Superia 800 approximation", ["street", "mixed-light night", "warm indoor"], ["neutral product photography", "delicate skin color", "deep noisy shadows"], [0.10, 0.25]),
    ("kodak_tri-x_400", "bw", "Pat David Tri-X 400 monochrome approximation", ["black-and-white", "street", "shape and texture studies"], ["color-critical scene", "sunset whose story depends on color"], [1.0, 1.0]),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interpolate(flat_table, size, rgb):
    """CUBE/Hald red-fastest table: index r + size*g + size**2*b."""
    shape = np.shape(rgb)
    coords = np.asarray(rgb, dtype=np.float64).reshape(-1, 3) * (size - 1)
    coords = np.clip(coords, 0, size - 1)
    lower = np.floor(coords).astype(np.int32)
    upper = np.minimum(lower + 1, size - 1)
    fraction = coords - lower
    result = np.zeros_like(coords)
    for rbit in (0, 1):
        for gbit in (0, 1):
            for bbit in (0, 1):
                r = upper[:, 0] if rbit else lower[:, 0]
                g = upper[:, 1] if gbit else lower[:, 1]
                b = upper[:, 2] if bbit else lower[:, 2]
                weight = np.ones(len(coords))
                for channel, bit in enumerate((rbit, gbit, bbit)):
                    weight *= fraction[:, channel] if bit else (1 - fraction[:, channel])
                result += flat_table[r + size * g + size * size * b] * weight[:, None]
    return result.reshape(shape)


def png_chunks(path):
    content = path.read_bytes()
    cursor = 8
    tags = []
    while cursor < len(content):
        length = struct.unpack(">I", content[cursor:cursor + 4])[0]
        tag = content[cursor + 4:cursor + 8].decode("ascii")
        tags.append(tag)
        cursor += length + 12
    return sorted(set(tags))


def load_hald(path):
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"Invalid RGB Hald asset: {path}")
    height, width, _ = image.shape
    level = int(round(width ** (1 / 3)))
    if height != width or level ** 3 != width:
        raise ValueError(f"Invalid Hald dimensions: {image.shape}")
    size = level * level
    maximum = np.iinfo(image.dtype).max
    table = image[:, :, ::-1].reshape(-1, 3).astype(np.float64) / maximum
    return table, size, {"width": width, "height": height, "level": level, "size": size, "bit_depth": image.dtype.itemsize * 8, "png_chunks": png_chunks(path)}


def convert_hald(path, name, source_url, size=33):
    source, source_size, source_info = load_hald(path)
    blue, green, red = np.meshgrid(*([np.linspace(0, 1, size)] * 3), indexing="ij")
    points = np.stack((red, green, blue), axis=-1).reshape(-1, 3)
    table = interpolate(source, source_size, points)
    destination = ROOT / PAT_DIR / f"{name}.cube"
    with destination.open("w", encoding="ascii", newline="\n") as out:
        out.write(f'# Pat David film-emulation approximation; not a measured film-stock transform.\n# License: CC-BY-SA-4.0 https://creativecommons.org/licenses/by-sa/4.0/\n# Source: {source_url}\n# Converted 2026-10-01: 16-bit Hald64 to CUBE33 by trilinear resampling.\n# Input/output: display-referred sRGB FAMILY ASSUMPTION; preview required.\n# RGB triples; red index changes fastest.\nTITLE "Pat David {name}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(out, table, fmt="%.9f")
    random_points = np.random.default_rng(20261001).random((20000, 3))
    error = interpolate(table, size, random_points) - interpolate(source, source_size, random_points)
    source_info["conversion_error"] = {
        "method": "RGB component absolute difference, CUBE33 vs original Hald64, 20000 uniform random RGB inputs; not a perceptual image-quality score",
        "max_abs_in_8bit_codes": round(float(np.max(np.abs(error)) * 255), 5),
        "rms_in_8bit_codes": round(float(np.sqrt(np.mean(error * error)) * 255), 5),
        "p99_abs_in_8bit_codes": round(float(np.percentile(np.abs(error), 99) * 255), 5),
    }
    return destination, source_info


def read_cube(path):
    size = None
    domain_min = [0.0, 0.0, 0.0]
    domain_max = [1.0, 1.0, 1.0]
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        tokens = line.split()
        if tokens[0] == "TITLE":
            continue
        if tokens[0] == "LUT_3D_SIZE":
            size = int(tokens[1])
        elif tokens[0] == "DOMAIN_MIN":
            domain_min = list(map(float, tokens[1:]))
        elif tokens[0] == "DOMAIN_MAX":
            domain_max = list(map(float, tokens[1:]))
        elif len(tokens) == 3:
            rows.append(list(map(float, tokens)))
        else:
            raise ValueError(f"Unsupported cube directive: {line}")
    table = np.asarray(rows, dtype=np.float64)
    if size is None or table.shape != (size ** 3, 3) or not np.isfinite(table).all():
        raise ValueError(f"Invalid CUBE shape or data: {path}")
    if domain_min != [0.0, 0.0, 0.0] or domain_max != [1.0, 1.0, 1.0]:
        raise ValueError(f"Non-unit CUBE domain: {path}")
    ramp_input = np.repeat(np.linspace(0, 1, 1025)[:, None], 3, axis=1)
    ramp = interpolate(table, size, ramp_input)
    luma = ramp @ np.array([0.2126, 0.7152, 0.0722])
    values = {str(v): [round(float(x), 5) for x in interpolate(table, size, [[v, v, v]])[0]] for v in (0, 0.02, 0.18, 0.5, 0.9, 0.98, 1)}
    probe_inputs = np.array([[0.65, 0.43, 0.31], [0.08, 0.27, 0.07], [0.12, 0.32, 0.7], [1, 0.45, 0.04]])
    probes = interpolate(table, size, probe_inputs)
    return {
        "size": size, "row_count": len(table), "domain_min": domain_min, "domain_max": domain_max,
        "all_finite": True, "min": round(float(table.min()), 9), "max": round(float(table.max()), 9),
        "out_of_unit_range_values": int(np.count_nonzero((table < 0) | (table > 1))),
        "neutral_ramp": {
            "method": "1025 encoded-RGB neutral samples; Rec.709-weighted encoded luma is a diagnostic, not scene-linear luminance",
            "samples_rgb": values,
            "luma_decreasing_steps": int(np.count_nonzero(np.diff(luma) < -1e-7)),
            "luma_flat_steps": int(np.count_nonzero(np.abs(np.diff(luma)) < 1e-7)),
            "largest_downward_step_in_8bit_codes": round(float(max(0, -np.min(np.diff(luma))) * 255), 6),
            "sum_downward_steps_in_8bit_codes": round(float(np.sum(np.maximum(-np.diff(luma), 0)) * 255), 6),
            "highlight_0_98_to_1_luma_difference_in_8bit_codes": round(float((luma[-1] - interpolate(table, size, [[0.98, 0.98, 0.98]])[0] @ np.array([0.2126, 0.7152, 0.0722])) * 255), 6),
            "max_rgb_spread": round(float(np.max(np.ptp(ramp, axis=1))), 6),
            "range_10_to_90": round(float(luma[922] - luma[102]), 6),
        },
        "synthetic_color_probes": {"input_rgb": probe_inputs.tolist(), "output_rgb": np.round(probes, 6).tolist(), "note": "Representative RGB probes only; not proof of accurate skin, foliage or gamut handling"},
    }


def relative(path):
    return path.relative_to(PROJECT).as_posix()


def build():
    luts = []
    for name, category, display_name, scenes, avoid, strength in PAT_LOOKS:
        source_url = f"https://raw.githubusercontent.com/NatronGitHub/clut/{PAT_COMMIT}/{category}/{name}.png"
        original = ROOT / PAT_DIR / "originals" / f"{name}.png"
        cube, original_info = convert_hald(original, name, source_url)
        luts.append({
            "id": f"pat_{name.replace('-', '_')}", "name": display_name, "path": relative(cube), "sha256": sha(cube),
            "source": {"author": "Pat David", "repository": "https://github.com/NatronGitHub/clut", "commit": PAT_COMMIT, "url": source_url, "original_path": relative(original), "original_sha256": sha(original), "original_info": original_info},
            "license": {"spdx": "CC-BY-SA-4.0", "license_path": f"assets/luts/{PAT_DIR}/LICENSE-CC-BY-SA-4.0.txt", "attribution_path": f"assets/luts/{PAT_DIR}/ATTRIBUTION.md", "evidence": f"https://github.com/NatronGitHub/clut/blob/{PAT_COMMIT}/README.md"},
            "color_space": {"input": "display-referred sRGB RGB [0,1] (family-level assumption)", "output": "display-referred sRGB RGB [0,1] (family-level assumption)", "status": "assumed_not_individually_verified", "evidence": ["https://rawpedia.rawtherapee.com/Film_Emulation", "https://patdavid.net/2015/03/film-emulation-in-rawtherapee/"], "note": "RawPedia documents sRGB for the related film-emulation collection. These 16-bit Natron originals have no sRGB/gAMA/ICC metadata; source README gives no per-file encoding. No ICC certification or exact camera-profile match is claimed."},
            "usage": {"scenes": scenes, "avoid": avoid, "initial_strength_range": strength, "auto_select": False, "recommendation_basis": "curatorial hypothesis from measured tone/color response, to be confirmed on each image; not a stock-name guarantee", "limitations": ["preview before use", "cannot recover clipped JPEG detail", "cannot add grain, halation, texture, local masks or denoising", "not a measured reproduction of named stock", "no Log/HDR/linear/AdobeRGB/P3 inputs without a known prior conversion"]},
            "validation": read_cube(cube),
        })
    for name, scenes, avoid, strength in [
        ("Meridian", ["daylight", "neutral baseline", "documentary"], ["assuming neutral means identity", "exact product color"], [0.15, 0.35]),
        ("Lowsun", ["golden hour", "warm backlight"], ["already strongly orange sunset", "neutral skin/product requirements", "excess cool shadow cast"], [0.10, 0.25]),
    ]:
        cube = ROOT / MIT_DIR / f"{name}.cube"
        luts.append({
            "id": f"lumix_{name.lower()}", "name": f"LUMIX original {name} (experimental sRGB candidate)", "path": relative(cube), "sha256": sha(cube),
            "source": {"author": "Zhengxiao Wu (t0saki), AI-assisted original mathematical design per upstream", "repository": "https://github.com/t0saki/lumix-original-looks", "commit": LUMIX_COMMIT, "url": f"https://raw.githubusercontent.com/t0saki/lumix-original-looks/{LUMIX_COMMIT}/luts/{name}.cube", "modifications": "none; original CUBE bytes preserved"},
            "license": {"spdx": "MIT", "license_path": f"assets/luts/{MIT_DIR}/LICENSE", "attribution_path": f"assets/luts/{MIT_DIR}/ATTRIBUTION.md", "evidence": f"https://github.com/t0saki/lumix-original-looks/blob/{LUMIX_COMMIT}/README.md"},
            "color_space": {"input": "LUMIX S9 Standard photo style + sRGB display-referred RGB [0,1]", "output": "sRGB display-referred RGB [0,1]", "status": "author_declared_profile_specific", "evidence": [f"https://github.com/t0saki/lumix-original-looks/blob/{LUMIX_COMMIT}/README.md"], "note": "Explicit sRGB basis, optimized for a specific already-rendered camera profile. Generic sRGB JPEG use is an experiment, not an author-certified profile match."},
            "usage": {"scenes": scenes, "avoid": avoid, "initial_strength_range": strength, "auto_select": False, "recommendation_basis": "author-declared scene intent plus measured neutral ramp; lower starting strengths are this project's cautious generic-JPEG policy, not the author's camera opacity settings", "limitations": ["generic-JPEG validation required", "not a faithful film-stock emulation", "AI-assisted upstream origin is explicit", "no Log/HDR/linear/AdobeRGB/P3 input without known prior conversion"]},
            "validation": read_cube(cube),
        })
    catalog = {
        "version": 1, "created_on": "2026-10-01", "purpose": "Small licensed creative LUT candidate library; manual/model visual judgment must precede selection.",
        "default_policy": "No automatic LUT choice. Use identity/no-LUT as the baseline. Confirm input encoding and preview at a conservative strength before applying. Measurements are diagnostics, not an aesthetic pass.",
        "cube_convention": "RGB triples; red fastest, green next, blue slowest; DOMAIN [0,1]; trilinear interpolation",
        "collections": [{"id": "pat-david", "license": "CC-BY-SA-4.0", "count": 6}, {"id": "lumix-original", "license": "MIT", "count": 2}],
        "luts": luts,
    }
    (ROOT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in luts:
        ramp = item["validation"]["neutral_ramp"]
        print(item["id"], "black/white", ramp["samples_rgb"]["0"], ramp["samples_rgb"]["1"], "decreases", ramp["luma_decreasing_steps"], "flat", ramp["luma_flat_steps"], "maxcast", ramp["max_rgb_spread"])


if __name__ == "__main__":
    build()
