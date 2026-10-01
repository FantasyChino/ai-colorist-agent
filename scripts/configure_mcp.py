"""Print configuration for this checkout; optionally register it with Codex."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true", help="Run codex mcp add for this checkout")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    python = str(Path(sys.executable).resolve())
    server = str(root / "server/mcp_server.py")
    if args.register:
        subprocess.run(["codex", "mcp", "add", "ai-colorist", "--", python, server], check=True)
    else:
        print(json.dumps({"mcpServers": {"ai-colorist": {
            "command": python, "args": [server], "cwd": str(root)
        }}}, indent=2))


if __name__ == "__main__":
    main()
