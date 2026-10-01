"""Render independent public fixtures through the existing OpenCV LUT pipeline."""
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.look_library import list_looks
from tools.lut_engine import load_cube, apply_simple_lut


def main():
    destination = ROOT / "docs/images"
    destination.mkdir(parents=True, exist_ok=True)
    entries = [e for e in list_looks()["looks"] if e["id"].startswith("ac_")]
    samples = ["astronaut.png", "coffee.png", "chelsea.png", "rocket.jpg"]
    results = []
    for sample in samples:
        source = cv2.imread(str(ROOT / "tests/fixtures" / sample))
        if source is None:
            raise ValueError(f"Missing or unreadable fixture: {sample}")
        cells = [("Original", source)]
        for entry in entries:
            # Full strength makes differences assessable; it is not a universal recommendation.
            output = apply_simple_lut(source, load_cube(ROOT / entry["path"]))
            cells.append((entry["name"], output))
            results.append({"sample": sample, "look": entry["id"], "strength": 1.0,
                            "mean_absolute_channel_change": round(float(cv2.absdiff(output, source).mean()), 3),
                            "source_endpoint_channel_fraction": round(float(((source == 0) | (source == 255)).mean()), 6),
                            "output_endpoint_channel_fraction": round(float(((output == 0) | (output == 255)).mean()), 6)})
        canvas = np.full((3 * 258, 4 * 280, 3), 24, dtype=np.uint8)
        for i, (name, image) in enumerate(cells):
            scale = min(280 / image.shape[1], 228 / image.shape[0])
            scaled = cv2.resize(image, (round(image.shape[1]*scale), round(image.shape[0]*scale)), interpolation=cv2.INTER_AREA)
            y, x = (i//4)*258+30, (i%4)*280
            x += (280-scaled.shape[1])//2
            canvas[y:y+scaled.shape[0], x:x+scaled.shape[1]] = scaled
            cv2.putText(canvas, name, ((i%4)*280+8, (i//4)*258+21), cv2.FONT_HERSHEY_SIMPLEX, .45, (235,235,235), 1, cv2.LINE_AA)
        cv2.imwrite(str(destination / f"looks-{Path(sample).stem}.jpg"), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
    report = {"version": "1.0.0", "method": "40 independent fixture/look combinations at full strength; channel metrics are not aesthetic judgments.", "results": results}
    (ROOT / "docs/look-validation.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"combinations": len(results), "contact_sheets": 4}))


if __name__ == "__main__":
    main()
