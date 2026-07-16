#!/usr/bin/env bash
# One-command connect: registers this server with Claude Code, or prints config
# for other MCP clients if the `claude` CLI isn't installed. Safe to re-run.
#
#   ./connect.sh            read-only (the default: the agent can look, not touch)
#   ./connect.sh --writes   grant writes — an explicit human decision, on purpose
set -euo pipefail
cd "$(dirname "$0")"

WRITES=0
[ "${1:-}" = "--writes" ] && WRITES=1

PY="$PWD/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "No .venv here yet — run ./setup.sh first (it builds everything and self-tests)."
  exit 1
fi

if command -v claude >/dev/null 2>&1; then
  claude mcp remove filevine >/dev/null 2>&1 || true   # re-runs shouldn't error
  claude mcp add filevine --env FILEVINE_MCP_ALLOW_WRITES=$WRITES -- "$PY" "$PWD/server.py"
  echo
  echo "Connected. Two steps left:"
  echo
  echo "  1. Start Claude Code from THIS folder:    claude"
  echo "  2. Ask it:   What needs attention across our matters this morning?"
  echo
  if [ "$WRITES" = "1" ]; then
    echo "Writes are ON: the agent can create tasks/notes and execute workflows on the"
    echo "mock org — every call still lands in audit.jsonl. (Back to read-only: ./connect.sh)"
  else
    echo "The server is registered for this folder only, and writes are OFF — the agent"
    echo "can look, not touch. When it refuses a write, that's the governance working."
    echo "To grant writes (one command, deliberately human):   ./connect.sh --writes"
  fi
  echo "(Undo anytime:  claude mcp remove filevine)"
else
  echo "Claude Code's 'claude' command isn't on this machine's PATH."
  echo "Config for other MCP clients (Claude Desktop, Cursor, Inspector):"
  echo
  exec "$PY" setup_helper.py
fi
