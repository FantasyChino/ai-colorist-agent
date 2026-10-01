# MCP setup and execution

Create `.venv`, install `requirements.txt`, then run that environment's Python:

```text
python scripts/configure_mcp.py
```

This prints `mcpServers.ai-colorist` with the actual absolute Python/server paths
on your machine. Use the JSON with a compatible MCP client. For an installed
Codex CLI, run `python scripts/configure_mcp.py --register` instead. The CLI
stores its own configuration; generated JSON is not Codex's TOML configuration.
Reconnect/reload the client afterwards.

For an Agent Plugins 1.0 host, `mcp.json` uses `${PLUGIN_ROOT}` and
`scripts/launch_server.py`. The launcher finds `.venv/Scripts/python.exe` on
Windows or `.venv/bin/python` on POSIX. Initial `python` must be on PATH.
Direct registration is the fallback for hosts that do not load packages.
Image viewing and project skills must also be available in the host.

Direct startup is `python server/mcp_server.py`. A stdio server normally waits
for protocol input without a startup banner. `python server/smoke_test.py`
starts an actual client, discovers six tools, tests the connection, lists/prepares
a look and grades a public fixture. It also checks optional analysis and errors.

Actual schemas are exported in `schemas/tool_schema.json`. Optional analysis
matches `schemas/photo_analysis_schema.json`. Executable grading controls are in
`schemas/execution_strategy_schema.json`; this documentation schema is not yet
enforced by the runtime. `color_strategy_schema.json` is an artistic planning
schema, so subject protection/texture fields do not promise implemented processing.

Relative image/LUT paths resolve against the checkout, independent of launch cwd.
`apply_color_grade` replaces root `output.jpg`; use distinct input paths and
save candidates separately. Serialize calls to this fixed-output tool.

The model inspects the input, reads project skills, invokes processing and then
inspects actual output. Pixel analysis/reference fitting are optional. Ordinary
use of included LUTs requires no reference corpus or training.

Protocol tests verify local startup/processing. Manifest validation does not
certify every host or constitute a plugin-store submission.
