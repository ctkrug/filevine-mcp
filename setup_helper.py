"""setup_helper.py — prints copy-paste connection config for THIS checkout.

Backlog issue A2 ("one-string connection setup") applied to the kit itself: no
placeholder /path/to/ edits, no guessing which python. Run it, paste the block
for your client, done.

Run:  .venv/bin/python setup_helper.py   (plain python3 works too — stdlib only)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
CANDIDATES = [ROOT / ".venv" / "bin" / "python", ROOT / ".venv" / "Scripts" / "python.exe"]
PYTHON = next((str(p) for p in CANDIDATES if p.exists()), None)

if PYTHON is None:
    sys.exit("No .venv found next to server.py — run ./setup.sh first (Windows: "
             "py -3 -m venv .venv && .venv\\Scripts\\pip install mcp).")

print("filevine-mcp — connection config for this checkout")
print("=" * 60)

print("\n[1] Claude Code (one command):\n")
print(f"  claude mcp add filevine -- {PYTHON} {SERVER}")

print("\n[2] Claude Desktop — merge into claude_desktop_config.json,")
print("    then fully restart the app:\n")
print(json.dumps({
    "mcpServers": {
        "filevine": {
            "command": PYTHON,
            "args": [str(SERVER)],
            "env": {"FILEVINE_MCP_ALLOW_WRITES": "0"},
        }
    }
}, indent=2))

print("\n[3] Any other MCP client (Cursor, custom agents, ...):")
print(f"    command: {PYTHON}")
print(f"    args:    [{SERVER}]")

print("\n[4] No Claude account handy? Poke the tools directly in a browser")
print("    with the official MCP Inspector (needs Node):\n")
print(f"  npx @modelcontextprotocol/inspector {PYTHON} {SERVER}")

print("\nWrites are OFF by default. To let the agent create tasks/notes and")
print("execute workflows, set FILEVINE_MCP_ALLOW_WRITES=1 in the env block —")
print("that explicit human step is a feature, not friction.")
