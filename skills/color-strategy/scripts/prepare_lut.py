"""Bake a licensed creative LUT's strength into a standard red-fastest cube.

This blends encoded RGB with identity; it is not a technical color transform.
"""

import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.lut_engine import load_cube


def catalog_entries():
    catalog = json.loads((PROJECT_ROOT / "assets/luts/catalog.json").read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in catalog["luts"]}


def mixed_lut(entry, strength):
    """Validate the licensed source, then mix its table with the identity table."""
    if not math.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("Strength must be finite and between 0 and 1")
    source = PROJECT_ROOT / entry["path"]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        raise ValueError(f"Source checksum mismatch: {source}")
    lut = load_cube(source)
    if not np.array_equal(lut["domain_min"], [0, 0, 0]) or not np.array_equal(lut["domain_max"], [1, 1, 1]):
        raise ValueError("Only unit-domain creative LUTs from this catalog can be mixed")
    if np.any(lut["table"] < 0) or np.any(lut["table"] > 1):
        raise ValueError("Catalog creative LUT must have unit-range outputs")
    blue, green, red = np.indices((lut["size"],) * 3, dtype=np.float32)
    identity = np.stack((red, green, blue), axis=-1).reshape(-1, 3) / (lut["size"] - 1)
    return {**lut, "table": identity * (1 - strength) + lut["table"] * strength}


def default_output(lut_id, strength):
    return PROJECT_ROOT / "assets/luts/derived" / lut_id / f"strength-{strength:.6f}.cube"


def derived_paths(output):
    output = Path(output).resolve()
    return {"lut": output, "license": output.with_suffix(".license.txt"), "attribution": output.with_suffix(".attribution.md"), "provenance": output.with_suffix(".provenance.json")}


def prepare_lut(lut_id, strength, output=None):
    entries = catalog_entries()
    if lut_id not in entries:
        raise ValueError(f"Unknown LUT id {lut_id!r}; choose from {', '.join(entries)}")
    entry = entries[lut_id]
    lut = mixed_lut(entry, strength)
    output = Path(output) if output else default_output(lut_id, strength)
    output = (PROJECT_ROOT / output).resolve() if not output.is_absolute() else output.resolve()
    if not output.is_relative_to(PROJECT_ROOT):
        raise ValueError("Derived assets must be saved within the project")
    if output.suffix.lower() != ".cube":
        raise ValueError("Output must be a .cube path")
    protected = {str((PROJECT_ROOT / item["path"]).resolve()).casefold() for item in entries.values()}
    if str(output).casefold() in protected:
        raise ValueError("Cannot overwrite a catalog source")
    output.parent.mkdir(parents=True, exist_ok=True)
    license_source = PROJECT_ROOT / entry["license"]["license_path"]
    attribution_source = PROJECT_ROOT / entry["license"]["attribution_path"]
    paths = derived_paths(output)
    license_target = paths["license"]
    attribution_target = paths["attribution"]
    shutil.copyfile(license_source, license_target)
    attribution_target.write_text(
        f'# Derived asset: {output.name}\n\n'
        f'Original author: {entry["source"]["author"]}. License: {entry["license"]["spdx"]}.\n'
        f'Source: {entry["source"]["url"]}\nSource CUBE SHA-256: {entry["sha256"]}\n\n'
        f'Modification: encoded RGB identity blend at strength {strength:.10g}; no color-space conversion.\n'
        'This derivative retains the source license. The upstream notice below describes the original asset, not this modified CUBE.\n\n'
        '---\n\n' + attribution_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(f'# Derived from {entry["source"]["url"]}\n')
        stream.write(f'# Author: {entry["source"]["author"]}; License: {entry["license"]["spdx"]}\n')
        stream.write(f'# Modification: encoded RGB identity blend, strength={strength:.10g}\n')
        stream.write(f'TITLE "{lut_id} strength {strength:.10g}"\nLUT_3D_SIZE {lut["size"]}\n')
        stream.write("DOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n")
        np.savetxt(stream, lut["table"], fmt="%.9f")
    provenance = {
        "source_id": lut_id,
        "source_path": entry["path"],
        "source_sha256": entry["sha256"],
        "source": entry["source"],
        "license": entry["license"]["spdx"],
        "license_path": str(license_target),
        "attribution_path": str(attribution_target),
        "modification": "encoded RGB table = (1-strength)*identity + strength*source; no color-space conversion",
        "strength": strength,
        "color_space": entry["color_space"],
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "lut_path": str(output),
    }
    sidecar = paths["provenance"]
    sidecar.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"source_id": lut_id, "strength": strength, "lut_path": str(output), "provenance_path": str(sidecar)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lut_id")
    parser.add_argument("--strength", type=float, required=True)
    parser.add_argument("--output", help="Optional project-relative .cube path")
    args = parser.parse_args()
    try:
        result = prepare_lut(args.lut_id, args.strength, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
