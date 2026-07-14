#!/usr/bin/env python3
"""
test_evergreen.py — prove the demo reads identically no matter what day it runs.

The fixtures claim (server.py MockBackend docstring) that every relative number is
constant "no matter when you run it": Hale's SOL always 81 days out, the blown
meet-and-confer window always closed 12 days ago, and so on. That guarantee is the
whole reason a reviewer can clone this repo six months from now and see the same demo.

Nothing else exercises it — test_smoke runs on exactly one day (today). This does the
time travel: it drives the real server via FILEVINE_TODAY set to dates spread across
years (and a leap day), captures the full deadline + overdue signature at each, and
asserts every one matches the baseline exactly. If any date-math edge case (month
rollover, leap year, large shift) drifts a single number, this fails loudly.

Run: .venv/bin/python test_evergreen.py
"""
import asyncio
import json
import os
import sys
from datetime import date, timedelta

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    sys.exit("The 'mcp' package isn't installed here — run ./setup.sh first.")

# Simulated "today" values, all measured from the fixture anchor so the run is
# deterministic regardless of the real calendar date. Chosen to stress the date math:
# same day, a month, half a year, a full year, a leap-day crossing, and a multi-year shift.
ANCHOR = date(2026, 7, 13)
OFFSETS = [0, 30, 180, 365, 600, 1000]          # days after the anchor
DATES = [(ANCHOR + timedelta(days=d)).isoformat() for d in OFFSETS]
DATES.append("2028-02-29")                        # explicit leap day


async def signature_for(today: str) -> dict:
    """Full relative-time signature of the demo as seen on `today`."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        env={**os.environ, "FILEVINE_TODAY": today,
             "FILEVINE_FIXTURE_ANCHOR": ANCHOR.isoformat(),
             "FILEVINE_MCP_ALLOW_WRITES": "0"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            async def call(tool, args=None):
                res = await s.call_tool(tool, args or {})
                return json.loads(res.content[0].text)

            deadlines = await call("get_deadlines")
            health = await call("matter_health_report")

    # Keep only the relative-time facts; drop absolute dates (those SHOULD move).
    dl = {
        f'{d["project"]}|{d["rule"]}': d["daysRemaining"]
        for d in deadlines["deadlines"]
    }
    overdue = {x["task"]: x["daysOverdue"] for x in health.get("overdueTasks", [])}
    stale = {x["projectId"]: x["daysSinceActivity"] for x in health.get("staleMatters", [])}
    return {"deadlines": dl, "overdue": overdue, "stale": stale}


async def main() -> int:
    baseline = await signature_for(DATES[0])
    if not baseline["deadlines"]:
        print("  FAIL  baseline produced no deadlines — fixtures or tool broken")
        return 1

    failures = 0
    print(f"  baseline @ {DATES[0]}: "
          f'{len(baseline["deadlines"])} deadlines, '
          f'{len(baseline["overdue"])} overdue, {len(baseline["stale"])} stale')
    for today in DATES[1:]:
        sig = await signature_for(today)
        if sig == baseline:
            print(f"  PASS  today={today}: every relative number identical to baseline")
        else:
            failures += 1
            print(f"  FAIL  today={today}: drift from baseline")
            for section in ("deadlines", "overdue", "stale"):
                for k, v in baseline[section].items():
                    got = sig[section].get(k, "<missing>")
                    if got != v:
                        print(f"          {section}[{k}]: baseline {v} -> {got}")
                for k in sig[section]:
                    if k not in baseline[section]:
                        print(f"          {section}[{k}]: appeared only at {today} ({sig[section][k]})")

    print()
    if failures:
        print(f"  {failures} date(s) drifted — the demo is NOT evergreen. Fix before shipping.")
        return 1
    print(f"  Evergreen confirmed across {len(DATES)} dates spanning "
          f"{ANCHOR} .. 2028-02-29. Same demo on any calendar day.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
