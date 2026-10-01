"""Launch the prepared checkout's virtualenv without relying on its activation."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if not python.is_file():
    print("Create .venv and install requirements.txt before starting AI Colorist.", file=sys.stderr)
    raise SystemExit(1)
os.execv(str(python), [str(python), str(ROOT / "server/mcp_server.py")])
