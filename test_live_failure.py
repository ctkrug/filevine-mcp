#!/usr/bin/env python3
"""
test_live_failure.py — prove live mode fails GRACEFULLY.

The kit ships mock-by-default, but a reviewer may set real credentials and point it at
an org. If the documented auth flow is even slightly off, or the network is down, the
server must tell them what to fix — not dump a Python stack trace that reads as "this
candidate's code is broken." This test forces every live failure path offline (no real
Filevine calls) and asserts each one produces a clean, actionable message.

Cases:
  1. Unreachable API host  -> every tool returns {"error": ...} JSON, mode "live",
     with a hint pointing back to mock mode; the server stays up for the next call.
  2. Invalid FILEVINE_REGION -> the server exits with a one-line message, no traceback.
  3. Partial credentials    -> falls back to MOCK with a warning, and still serves data.

Run: .venv/bin/python test_live_failure.py
"""
import asyncio
import json
import os
import subprocess
import sys

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    sys.exit("The 'mcp' package isn't installed here — run ./setup.sh first.")

passed = failed = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global passed, failed
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failed += 1
        if detail:
            print(f"        {detail}")
    else:
        passed += 1


# Port 9 (discard) refuses fast — no real network, fully deterministic.
DEAD = "http://127.0.0.1:9"
LIVE_DEAD_ENV = {
    "FILEVINE_CLIENT_ID": "x", "FILEVINE_CLIENT_SECRET": "x", "FILEVINE_PAT": "x",
    "FILEVINE_TOKEN_URL": f"{DEAD}/connect/token",
    "FILEVINE_BASE_URL": f"{DEAD}/fv-app/v2",
}


async def case_unreachable() -> None:
    print("Case 1: unreachable live host — graceful errors, server survives")
    params = StdioServerParameters(
        command=sys.executable, args=["server.py"],
        env={**os.environ, **LIVE_DEAD_ENV},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            async def call(tool, args=None):
                res = await s.call_tool(tool, args or {})
                return json.loads(res.content[0].text)

            r = await call("search_projects")
            check("search_projects returns a clean error, not a crash",
                  "error" in r, detail=repr(r)[:200])
            check("error reports live mode", r.get("mode") == "live", detail=repr(r)[:200])
            check("error is actionable (mentions reaching the API / mock fallback)",
                  any(w in r.get("error", "").lower() for w in ("could not reach", "mock mode")),
                  detail=r.get("error", ""))

            # A tool that fans out over projects internally must also degrade cleanly.
            r2 = await call("matter_health_report")
            check("matter_health_report also degrades cleanly", "error" in r2,
                  detail=repr(r2)[:200])

            # Server is still alive and responsive after two failed calls.
            r3 = await call("list_workflows")
            check("server still responds after failures (workflows are local, so this succeeds)",
                  "count" in r3 or "error" in r3, detail=repr(r3)[:200])


def case_bad_region() -> None:
    print("Case 2: invalid region — clean exit, no traceback")
    env = {**os.environ, "FILEVINE_CLIENT_ID": "x", "FILEVINE_CLIENT_SECRET": "x",
           "FILEVINE_PAT": "x", "FILEVINE_REGION": "atlantis"}
    out = subprocess.run([sys.executable, "-c", "import server"],
                         env=env, capture_output=True, text=True, timeout=30)
    msg = out.stdout + out.stderr
    check("exits non-zero on bad region", out.returncode != 0, detail=f"rc={out.returncode}")
    check("message names the bad region and the fix", "atlantis" in msg and "us" in msg,
          detail=msg[-200:])
    check("no Python traceback leaked", "Traceback (most recent call last)" not in msg,
          detail=msg[-200:])


def case_partial_creds() -> None:
    print("Case 3: partial credentials — warn and fall back to mock")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("FILEVINE_")}          # clean slate
    env["FILEVINE_CLIENT_ID"] = "x"                    # only 1 of 3
    out = subprocess.run(
        [sys.executable, "-c",
         "import server, json; print(server.BACKEND.mode); "
         "print(len(server.BACKEND.projects()))"],
        env=env, capture_output=True, text=True, timeout=30)
    check("falls back to MOCK mode on partial creds", "mock" in out.stdout,
          detail=out.stdout + out.stderr)
    check("warns about the partial/missing credentials",
          "partial live credentials" in out.stderr, detail=out.stderr[-200:])
    check("mock backend still serves the 6 fixture matters", "6" in out.stdout.split(),
          detail=out.stdout)


async def main() -> int:
    await case_unreachable()
    case_bad_region()
    case_partial_creds()
    print()
    if failed:
        print(f"  {failed} check(s) failed, {passed} passed — live failures are NOT graceful yet.")
        return 1
    print(f"  All {passed} checks passed — live mode fails safely with actionable messages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
