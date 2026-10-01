"""Test a licensed derived LUT through a fresh MCP process, preserving output.jpg."""

import asyncio
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.smoke_test import error_text, field, result_payload
from tools.pipeline import ColorPipeline

SPEC = importlib.util.spec_from_file_location("prepare_lut", ROOT / "skills/color-strategy/scripts/prepare_lut.py")
WORKFLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKFLOW)


async def run():
    original_path = ROOT / "tests/fixtures/coffee.png"
    input_digest = hashlib.sha256(original_path.read_bytes()).hexdigest()
    preview_path = original_path
    image = cv2.imdecode(np.frombuffer(preview_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Cannot decode public test fixture")
    baked = WORKFLOW.prepare_lut("pat_fuji_velvia_50", 0.15)
    strategy = {"exposure": 0, "tone_strategy": {"contrast": "medium", "black_point": "normal"}, "lut": str(Path(baked["lut_path"]).relative_to(ROOT))}
    expected_strategy = {**strategy, "lut": baked["lut_path"]}
    expected = ColorPipeline().run(image, expected_strategy)
    ok, expected_jpeg = cv2.imencode(".jpg", expected)
    assert ok
    output = ROOT / "output.jpg"
    previous = output.read_bytes() if output.exists() else None
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server/mcp_server.py")], cwd=str(ROOT / "server"))
    report = {"transport": "stdio", "mode": "legacy", "input_sha256": input_digest, "preview_resolution": {"width": image.shape[1], "height": image.shape[0]}}
    try:
        async with Client(parameters, mode="legacy", read_timeout_seconds=30) as client:
            listing = await client.list_tools()
            names = sorted(tool.name for tool in listing.tools)
            assert {"test_colorist", "apply_color_grade", "analyze_image"}.issubset(names), names
            report["tools"] = names
            connection = await client.call_tool("test_colorist", {})
            assert not field(connection, "is_error", "isError", False), error_text(connection)
            assert result_payload(connection) == {"status": "AI Colorist MCP running"}
            report["test_colorist"] = result_payload(connection)
            result = await client.call_tool("apply_color_grade", {"image_path": str(preview_path.relative_to(ROOT)), "strategy": strategy})
            assert not field(result, "is_error", "isError", False), error_text(result)
            report["apply_color_grade"] = result_payload(result)
            assert report["apply_color_grade"] == {"status": "success", "output": "output.jpg"}
            actual_bytes = output.read_bytes()
            assert actual_bytes == expected_jpeg.tobytes(), "MCP output differs from the current pipeline"
            actual = cv2.imdecode(np.frombuffer(actual_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            assert actual.shape == image.shape
            report["strategy"] = strategy
            report["output_sha256_during_test"] = hashlib.sha256(actual_bytes).hexdigest()
    finally:
        if previous is not None:
            output.write_bytes(previous)
        elif output.exists():
            output.unlink()
    assert hashlib.sha256(original_path.read_bytes()).hexdigest() == input_digest
    assert (output.read_bytes() if output.exists() else None) == previous
    report["input_preserved"] = True
    report["previous_output_preserved"] = True
    report["status"] = "passed"
    path = ROOT / "mcp-lut-test-results.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(run(), timeout=60))
