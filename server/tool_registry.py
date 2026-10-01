import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from jsonschema import Draft7Validator
from mcp.server.mcpserver.exceptions import ToolError

from tools.image_analyzer import analyze_image as analyze_image_file
from tools.pipeline import ColorPipeline
from tools.look_library import list_looks as list_looks_file, prepare_look as prepare_look_file
from tools.style_lut_learner import (
    ReferenceSetError,
    learn_style_lut as learn_style_lut_file,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHOTO_ANALYSIS_SCHEMA = json.loads(
    (PROJECT_ROOT / "schemas" / "photo_analysis_schema.json").read_text(encoding="utf-8")
)
Draft7Validator.check_schema(PHOTO_ANALYSIS_SCHEMA)
PHOTO_ANALYSIS_VALIDATOR = Draft7Validator(PHOTO_ANALYSIS_SCHEMA)


def register_tools(mcp: Any) -> None:
    """Register the existing color pipeline as MCP tools."""

    @mcp.tool()
    def test_colorist() -> dict[str, str]:
        """Test whether the AI Colorist MCP server is connected."""
        return {"status": "AI Colorist MCP running"}

    @mcp.tool()
    def list_looks() -> dict[str, Any]:
        """List bundled ready-to-use looks, scenes, encoding and license conditions.

        No training is required. Inspect the source photo before choosing a look.
        """
        return list_looks_file()

    @mcp.tool()
    def prepare_look(lut_id: str, strength: float = 0.65) -> dict[str, Any]:
        """Prepare a catalog look at strength 0..1, retaining license and provenance.

        Pass the returned lut_path to apply_color_grade's strategy.lut. This
        mixes encoded RGB with identity and performs no log/RAW conversion.
        """
        try:
            return prepare_look_file(lut_id, strength)
        except (OSError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool()
    def analyze_image(image_path: str) -> dict[str, Any]:
        """Analyze brightness, contrast, exposure, saturation, and dominant colors.

        Optional pixel statistics matching photo_analysis_schema.json.
        The host model should visually inspect the image for grading decisions.
        Relative paths use the project root. This does not recognize subjects.
        """
        try:
            analysis = analyze_image_file(image_path)
        except (OSError, ValueError) as exc:
            raise ToolError(str(exc)) from exc
        PHOTO_ANALYSIS_VALIDATOR.validate(analysis)
        return analysis

    @mcp.tool()
    def learn_style_lut(
        source_image_path: str,
        reference_dir: str,
        style_name: str,
        strength: float = 1.0,
    ) -> dict[str, Any]:
        """Fit a source-dependent creative CUBE LUT from 500+ reference photos.

        The references are analyzed locally with OpenCV and weighted one image per
        vote. The full corpus selects a source-compatible creative mode. This is
        an unpaired statistical color-distribution approximation,
        not recovery of a photographer's original editing curve. It writes a LUT,
        profile, and provenance manifest under assets/luts/learned; it never
        modifies the source or reference images. strength is between 0 and 2.
        """
        try:
            return learn_style_lut_file(
                source_image_path=source_image_path,
                reference_dir=reference_dir,
                style_name=style_name,
                strength=strength,
            )
        except ReferenceSetError as exc:
            raise ToolError(str(exc)) from exc
        except (OSError, ValueError, cv2.error) as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool()
    def apply_color_grade(
        image_path: str,
        strategy: dict[str, Any],
    ) -> dict[str, str]:
        """Grade an image and save output.jpg in the project root.

        Relative image and LUT paths are resolved against the project root.
        The strategy is passed to the existing ColorPipeline.
        """
        input_path = Path(image_path).expanduser()
        if not input_path.is_absolute():
            input_path = PROJECT_ROOT / input_path
        input_path = input_path.resolve()

        if not input_path.is_file():
            raise ToolError(f"Image file not found: {input_path}")

        try:
            image_bytes = np.fromfile(input_path, dtype=np.uint8)
        except OSError as exc:
            raise ToolError(f"Unable to read image: {input_path}: {exc}") from exc
        if image_bytes.size == 0:
            raise ToolError(f"Unable to read image: {input_path}")
        try:
            image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        except cv2.error as exc:
            raise ToolError(f"Unable to decode image: {input_path}") from exc
        if image is None:
            raise ToolError(f"Unable to decode image: {input_path}")

        pipeline_strategy = strategy
        if strategy.get("lut"):
            lut_path = Path(strategy["lut"]).expanduser()
            if not lut_path.is_absolute():
                pipeline_strategy = dict(strategy)
                pipeline_strategy["lut"] = str((PROJECT_ROOT / lut_path).resolve())

        result = ColorPipeline().run(image, pipeline_strategy)
        output_path = PROJECT_ROOT / "output.jpg"
        try:
            encoded, output_bytes = cv2.imencode(".jpg", result)
        except cv2.error as exc:
            raise ToolError(f"Unable to encode output image: {output_path}") from exc
        if not encoded:
            raise ToolError(f"Unable to encode output image: {output_path}")
        try:
            output_bytes.tofile(output_path)
        except OSError as exc:
            raise ToolError(f"Unable to save output image: {output_path}: {exc}") from exc

        return {"status": "success", "output": "output.jpg"}
