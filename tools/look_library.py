"""Expose the licensed catalog and existing strength preparation through MCP."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "colorist_prepare_lut", ROOT / "skills/color-strategy/scripts/prepare_lut.py"
)
_workflow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_workflow)


def list_looks():
    catalog = json.loads((ROOT / "assets/luts/catalog.json").read_text(encoding="utf-8"))
    return {"count": len(catalog["luts"]), "looks": catalog["luts"]}


def prepare_look(lut_id: str, strength: float = 0.65):
    return _workflow.prepare_lut(lut_id, strength)
