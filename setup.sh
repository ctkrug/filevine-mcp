#!/usr/bin/env bash
# One-command setup: finds a Python 3.10+, builds the venv, installs mcp, runs the
# smoke suite. Exists because macOS ships Python 3.9 as `python3` — the #1 way a
# cold clone of this repo would fail on someone else's machine.
set -euo pipefail
cd "$(dirname "$0")"

PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if command -v "$c" >/dev/null 2>&1 \
     && "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done

if [ -z "$PY" ]; then
  echo "No Python 3.10+ found (macOS's built-in python3 is 3.9)."
  echo "Install one first:  brew install python   — or grab it from python.org."
  exit 1
fi

echo "Using $PY ($("$PY" --version))"
"$PY" -m venv .venv
.venv/bin/pip install --quiet --upgrade pip mcp
echo
.venv/bin/python test_smoke.py
echo
echo "Ready. Next step — print the exact connection config for your MCP client:"
echo "  .venv/bin/python setup_helper.py"
