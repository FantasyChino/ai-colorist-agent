r"""Exercise the AI Colorist server through its real stdio MCP transport.

Run with ``.venv\Scripts\python.exe server\smoke_test.py`` from the project.
This is a protocol client, with no agent or LLM calls.
"""

import asyncio
import json
import tempfile
import sys
from pathlib import Path
from typing import Any

import cv2
from jsonschema import Draft7Validator
from mcp import Client, StdioServerParameters


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STRATEGY = {
    "exposure": 0,
    "tone_strategy": {"contrast": "medium", "black_point": "normal"},
    "color_strategy": {"saturation": "preserve"},
}


def field(value: Any, snake_name: str, camel_name: str, default: Any = None) -> Any:
    """Support SDK snake_case fields and JSON wire-format dictionaries."""
    if isinstance(value, dict):
        return value.get(snake_name, value.get(camel_name, default))
    return getattr(value, snake_name, getattr(value, camel_name, default))


def result_payload(result: Any) -> dict[str, Any]:
    structured = field(result, "structured_content", "structuredContent")
    if isinstance(structured, dict):
        return structured
    for block in field(result, "content", "content", []):
        if field(block, "type", "type") == "text":
            try:
                payload = json.loads(field(block, "text", "text", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                return payload
    raise AssertionError("MCP tool result has no JSON object payload")


def error_text(result: Any) -> list[str]:
    return [
        field(block, "text", "text", "")
        for block in field(result, "content", "content", [])
        if field(block, "type", "type") == "text"
    ]


async def smoke_test() -> dict[str, Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(PROJECT_ROOT / "server" / "mcp_server.py")],
        # Prove that image and output paths do not depend on launch cwd.
        cwd=str(PROJECT_ROOT / "server"),
    )
    report: dict[str, Any] = {"transport": "stdio", "mode": "legacy"}
    async with Client(parameters, mode="legacy", read_timeout_seconds=30) as client:
        listing = await client.list_tools()
        tools = {tool.name: tool for tool in listing.tools}
        assert {
            "test_colorist", "analyze_image", "learn_style_lut", "apply_color_grade", "list_looks", "prepare_look"
        }.issubset(tools), (
            f"Missing expected tools; discovered {sorted(tools)}"
        )

        test_schema = field(tools["test_colorist"], "input_schema", "inputSchema")
        assert test_schema.get("properties", {}) == {}, test_schema
        assert test_schema.get("required", []) == [], test_schema

        analysis_schema = field(tools["analyze_image"], "input_schema", "inputSchema")
        assert analysis_schema["properties"]["image_path"]["type"] == "string", analysis_schema
        assert analysis_schema.get("required", []) == ["image_path"], analysis_schema

        grade_schema = field(tools["apply_color_grade"], "input_schema", "inputSchema")
        properties = grade_schema.get("properties", {})
        assert properties["image_path"]["type"] == "string", grade_schema
        assert properties["strategy"]["type"] == "object", grade_schema
        assert {"image_path", "strategy"}.issubset(grade_schema.get("required", [])), grade_schema

        learn_schema = field(tools["learn_style_lut"], "input_schema", "inputSchema")
        learn_properties = learn_schema.get("properties", {})
        assert learn_properties["source_image_path"]["type"] == "string", learn_schema
        assert learn_properties["reference_dir"]["type"] == "string", learn_schema
        assert learn_properties["style_name"]["type"] == "string", learn_schema
        assert learn_properties["strength"]["type"] == "number", learn_schema
        assert {"source_image_path", "reference_dir", "style_name"}.issubset(
            learn_schema.get("required", [])
        ), learn_schema
        report["tools"] = {
            name: field(tool, "input_schema", "inputSchema")
            for name, tool in tools.items()
        }

        test_result = await client.call_tool("test_colorist", {})
        assert not field(test_result, "is_error", "isError", False), error_text(test_result)
        test_payload = result_payload(test_result)
        assert test_payload == {"status": "AI Colorist MCP running"}, test_payload
        report["test_colorist"] = test_payload

        input_path = PROJECT_ROOT / "tests" / "fixtures" / "coffee.png"
        assert input_path.is_file(), f"Test input missing: {input_path}"
        input_image = cv2.imread(str(input_path))
        assert input_image is not None, f"Cannot decode test input: {input_path}"

        analysis_result = await client.call_tool("analyze_image", {"image_path": "tests/fixtures/coffee.png"})
        assert not field(analysis_result, "is_error", "isError", False), error_text(analysis_result)
        analysis_payload = result_payload(analysis_result)
        required_fields = {"resolution", "brightness", "contrast", "exposure", "saturation", "dominant_colors"}
        assert required_fields.issubset(analysis_payload), analysis_payload
        photo_schema = json.loads(
            (PROJECT_ROOT / "schemas" / "photo_analysis_schema.json").read_text(encoding="utf-8")
        )
        Draft7Validator.check_schema(photo_schema)
        Draft7Validator(photo_schema).validate(analysis_payload)
        assert analysis_payload["resolution"] == {
            "width": int(input_image.shape[1]), "height": int(input_image.shape[0])
        }, analysis_payload
        assert analysis_payload["lighting"]["contrast"] == analysis_payload["contrast"]
        assert analysis_payload["technical"]["exposure"] == analysis_payload["exposure"]
        assert analysis_payload["color"]["saturation"] == analysis_payload["saturation"]
        assert analysis_payload["color"]["dominant_colors"] == analysis_payload["dominant_colors"]
        report["analyze_image"] = analysis_payload
        report["photo_analysis_schema"] = "passed"

        looks_result = await client.call_tool("list_looks", {})
        assert not field(looks_result, "is_error", "isError", False)
        assert result_payload(looks_result)["count"] == 18
        prepared = await client.call_tool("prepare_look", {"lut_id": "ac_teal_gold", "strength": 0.8})
        assert not field(prepared, "is_error", "isError", False), error_text(prepared)
        prepared_payload = result_payload(prepared)
        report["prepare_look"] = {"source_id": prepared_payload["source_id"], "strength": 0.8}
        grade_result = await client.call_tool(
            "apply_color_grade", {"image_path": "tests/fixtures/coffee.png", "strategy": {**STRATEGY, "lut": prepared_payload["lut_path"]}}
        )
        assert not field(grade_result, "is_error", "isError", False), error_text(grade_result)
        grade_payload = result_payload(grade_result)
        assert grade_payload == {"status": "success", "output": "output.jpg"}, grade_payload

        output_path = PROJECT_ROOT / "output.jpg"
        assert output_path.is_file(), f"Output missing: {output_path}"
        output_bytes = output_path.stat().st_size
        assert output_bytes > 0, "Output image is empty"
        output_image = cv2.imread(str(output_path))
        assert output_image is not None, "Output is not a decodable image"
        assert output_image.shape == input_image.shape, (
            f"Image dimensions changed: {input_image.shape} -> {output_image.shape}"
        )
        assert cv2.absdiff(output_image, input_image).mean() > 1, "Look produced no visible numeric change"
        report["apply_color_grade"] = grade_payload
        report["workflow"] = ["list_looks", "prepare_look", "apply_color_grade"]
        report["output_image"] = {
            "path": str(output_path),
            "bytes": output_bytes,
            "width": int(output_image.shape[1]),
            "height": int(output_image.shape[0]),
            "channels": int(output_image.shape[2]),
        }

        with tempfile.TemporaryDirectory(prefix="colorist-smoke-", dir=PROJECT_ROOT) as temporary:
            temporary_path = Path(temporary)
            missing_result = await client.call_tool(
                "apply_color_grade",
                {"image_path": str(temporary_path / "missing.jpg"), "strategy": STRATEGY},
            )
            assert field(missing_result, "is_error", "isError", False), (
                "A missing input must return an MCP tool error"
            )
            assert any("Image file not found" in text for text in error_text(missing_result)), (
                error_text(missing_result)
            )

            invalid_path = temporary_path / "invalid.jpg"
            invalid_path.write_bytes(b"This file is deliberately not an image.")
            invalid_result = await client.call_tool(
                "apply_color_grade", {"image_path": str(invalid_path), "strategy": STRATEGY}
            )
            assert field(invalid_result, "is_error", "isError", False), (
                "An invalid image must return an MCP tool error"
            )
            assert any("Unable to decode image" in text for text in error_text(invalid_result)), (
                error_text(invalid_result)
            )
            report["error_cases"] = {
                "missing_image": {"isError": True, "content": error_text(missing_result)},
                "invalid_image": {"isError": True, "content": error_text(invalid_result)},
            }
            analysis_errors = {}
            for case, path, expected in (
                ("missing_image", temporary_path / "missing.jpg", "Image file not found"),
                ("invalid_image", invalid_path, "Unable to decode image"),
            ):
                result = await client.call_tool("analyze_image", {"image_path": str(path)})
                assert field(result, "is_error", "isError", False), error_text(result)
                assert any(expected in text for text in error_text(result)), error_text(result)
                analysis_errors[case] = {"isError": True, "content": error_text(result)}
            report["analyze_image_error_cases"] = analysis_errors

            insufficient_result = await client.call_tool(
                "learn_style_lut",
                {
                    "source_image_path": "tests/fixtures/coffee.png",
                    "reference_dir": str(temporary_path),
                    "style_name": "insufficient-smoke-test",
                    "strength": 1.0,
                },
            )
            assert field(insufficient_result, "is_error", "isError", False), (
                "A reference set below 500 unique decodable images must return an MCP tool error"
            )
            assert any(
                "At least 500 unique decodable reference images are required" in text
                for text in error_text(insufficient_result)
            ), error_text(insufficient_result)
            report["learn_style_lut_error_case"] = {
                "isError": True, "content": error_text(insufficient_result)
            }
    report["status"] = "passed"
    return report


if __name__ == "__main__":
    output = PROJECT_ROOT / "output.jpg"
    original = output.read_bytes() if output.exists() else None
    try:
        print(json.dumps(asyncio.run(asyncio.wait_for(smoke_test(), timeout=60)), indent=2, ensure_ascii=False))
    finally:
        if original is not None:
            output.write_bytes(original)
        else:
            output.unlink(missing_ok=True)
