# Contributing

Keep MCP → Tools → OpenCV and preserve tested interfaces. Reproduce a processing
bug before changing an existing algorithm. Add new capabilities in separate
modules with thin wrappers and relevant skills. Do not add a new agent or GPT API
dependency to ordinary grading.

Use the project venv. Run unit tests and both protocol tests in README. For LUT
changes verify checksums, encoding, provenance, gradients and actual photographic
output. Numeric differences are not an aesthetic pass. Show same-size comparisons
where appropriate, using photos you may redistribute.

Do not commit environments, credentials, private originals, portfolio caches or
local fitted LUTs. Retain separate asset licenses. Update documentation/skills
after interface changes; run `python scripts/export_tool_catalog.py` to regenerate
the actual tool catalog.
