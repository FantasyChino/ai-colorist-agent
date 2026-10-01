"""Start the AI Colorist MCP server over stdio."""

import sys
from pathlib import Path

# Direct script execution adds server/, rather than the project root, to sys.path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer

from server.tool_registry import register_tools


mcp = MCPServer(
    "AI Colorist",
    instructions=(
        "For photographic grading, visually inspect the original image with the host model, "
        f"then read {PROJECT_ROOT / 'skills' / 'color-strategy' / 'SKILL.md'} before choosing "
        "supported controls or licensed LUTs. Apply the strategy with apply_color_grade and "
        "visually compare the actual output. learn_style_lut can fit a source-dependent "
        "statistical LUT from at least 500 locally cached reference photographs; treat its "
        "profile as an approximation rather than an author's original recipe. "
        "analyze_image is optional pixel statistics, "
        "not a required step or a substitute for the model's photographic judgment."
    ),
)
register_tools(mcp)


if __name__ == "__main__":
    mcp.run(transport="stdio")
