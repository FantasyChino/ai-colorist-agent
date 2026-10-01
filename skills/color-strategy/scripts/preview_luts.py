"""Render catalog LUT candidates through the existing pipeline, for visual review."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

from prepare_lut import PROJECT_ROOT, catalog_entries, default_output, derived_paths, prepare_lut

sys.path.insert(0, str(PROJECT_ROOT))
from tools.pipeline import ColorPipeline


def save_png(path, image):
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError(f"Could not encode {path}")
    encoded.tofile(path)


def diagnostic(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return {
        "gray_percentiles_1_50_99": np.percentile(gray, [1, 50, 99]).round(2).tolist(),
        "any_channel_at_255_percent": round(float(np.any(image == 255, axis=2).mean() * 100), 4),
        "all_channels_at_0_percent": round(float(np.all(image == 0, axis=2).mean() * 100), 4),
    }


def card(image, title):
    canvas = np.full((430, 600, 3), 28, dtype=np.uint8)
    scale = min(600 / image.shape[1], 390 / image.shape[0])
    resized = cv2.resize(image, (round(image.shape[1] * scale), round(image.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    top, left = (390 - resized.shape[0]) // 2, (600 - resized.shape[1]) // 2
    canvas[top:top + resized.shape[0], left:left + resized.shape[1]] = resized
    cv2.putText(canvas, title, (12, 416), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (240, 240, 240), 1, cv2.LINE_AA)
    return canvas


def preview(image_path, ids=None, strength=None, output_dir="demo/lut-previews", max_edge=1200):
    if max_edge < 64 or max_edge > 2400:
        raise ValueError("Preview maximum edge must be between 64 and 2400")
    if strength is not None and (not math.isfinite(strength) or not 0 <= strength <= 1):
        raise ValueError("Strength must be finite and between 0 and 1")
    entries = catalog_entries()
    selected = list(entries) if ids is None else ids
    if not selected or any(lut_id not in entries for lut_id in selected):
        raise ValueError("Select one or more valid catalog ids")
    source = Path(image_path)
    source = (PROJECT_ROOT / source).resolve() if not source.is_absolute() else source.resolve()
    source_bytes = source.read_bytes()
    original = cv2.imdecode(np.frombuffer(source_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if original is None:
        raise ValueError(f"Cannot decode {source}")
    scale = min(1, max_edge / max(original.shape[:2]))
    image = cv2.resize(original, (round(original.shape[1] * scale), round(original.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    directory = Path(output_dir)
    directory = (PROJECT_ROOT / directory).resolve() if not directory.is_absolute() else directory.resolve()
    if not directory.is_relative_to(PROJECT_ROOT):
        raise ValueError("Preview output must be within the project")
    planned = [directory / "original-preview.png", directory / "contact-sheet.jpg", directory / "preview-report.json"]
    planned += [directory / f"{lut_id}.png" for lut_id in selected]
    amounts = {}
    for lut_id in selected:
        low, high = entries[lut_id]["usage"]["initial_strength_range"]
        amounts[lut_id] = strength if strength is not None else min(high, max(low, 0.25))
        planned.extend(derived_paths(default_output(lut_id, amounts[lut_id])).values())
    if any(source == path.resolve() or (path.exists() and source.samefile(path)) for path in planned):
        raise ValueError("Preview output cannot overwrite the input")
    directory.mkdir(parents=True, exist_ok=True)
    save_png(planned[0], image)
    report = {
        "input": str(source), "input_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "original_resolution": {"width": original.shape[1], "height": original.shape[0]},
        "preview_resolution": {"width": image.shape[1], "height": image.shape[0]},
        "baseline": diagnostic(image),
        "note": "Resized previews, no ICC conversion; statistics are diagnostics, not aesthetic scores. Original unchanged.",
        "candidates": [],
    }
    cards = [card(image, "Original / no LUT")]
    for lut_id in selected:
        entry = entries[lut_id]
        amount = amounts[lut_id]
        baked = prepare_lut(lut_id, amount)
        strategy = {"exposure": 0, "tone_strategy": {"contrast": "medium", "black_point": "normal"}, "lut": baked["lut_path"]}
        pipeline = ColorPipeline()
        result = pipeline.run(image.copy(), strategy)
        path = directory / f"{lut_id}.png"
        save_png(path, result)
        report["candidates"].append({**baked, "output": str(path), "strategy": strategy, "history": pipeline.history, "diagnostic": diagnostic(result)})
        cards.append(card(result, f"{lut_id} / {amount:.0%}"))
    rows = math.ceil(len(cards) / 3)
    sheet = np.full((rows * 430, 3 * 600, 3), 28, dtype=np.uint8)
    for index, tile in enumerate(cards):
        row, column = divmod(index, 3)
        sheet[row * 430:(row + 1) * 430, column * 600:(column + 1) * 600] = tile
    sheet_path = directory / "contact-sheet.jpg"
    ok, encoded = cv2.imencode(".jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        raise ValueError("Could not encode contact sheet")
    encoded.tofile(sheet_path)
    report["contact_sheet"] = str(sheet_path)
    report_path = directory / "preview-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"count": len(selected), "contact_sheet": str(sheet_path), "report": str(report_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_path")
    parser.add_argument("--ids", nargs="+", help="Catalog ids; omit to preview all eight")
    parser.add_argument("--strength", type=float, help="Override all strengths, including black-and-white; default uses catalog ranges")
    parser.add_argument("--output-dir", default="demo/lut-previews")
    parser.add_argument("--max-edge", type=int, default=1200)
    args = parser.parse_args()
    try:
        result = preview(args.image_path, args.ids, args.strength, args.output_dir, args.max_edge)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
