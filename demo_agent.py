"""demo_agent.py — a scripted MCP client that runs the full 'morning triage' demo
against server.py and records everything it did.

Why scripted rather than an LLM: the point is to exercise the MCP surface
deterministically (same philosophy as driving order execution through a pure-Python
MCP client in my trading stack — zero tokens where none are needed). Point any real
MCP client (Claude Code / Claude Desktop) at server.py and it can improvise the same
session; this script just makes the canonical demo reproducible.

Produces:
  demo/transcript.json   structured record (feeds the showcase replay)
  demo/transcript.md     human-readable version

Run:  .venv/bin/python demo_agent.py
"""

import sys

if sys.version_info < (3, 10):
    sys.exit("demo_agent.py needs Python 3.10+ — run ./setup.sh, then "
             ".venv/bin/python demo_agent.py")

import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    sys.exit("The 'mcp' package isn't installed here — run ./setup.sh, then "
             ".venv/bin/python demo_agent.py")

HERE = Path(__file__).parent
DEMO_DIR = HERE / "demo"
AUDIT = HERE / "audit.jsonl"

STEPS: list[dict] = []


def _server(writes: bool) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
        env={**os.environ, "FILEVINE_MCP_ALLOW_WRITES": "1" if writes else "0"},
    )


def record(phase: str, beat: str, narration: str, tool: str | None,
           args: dict | None, result: dict | str | None) -> None:
    STEPS.append({"step": len(STEPS) + 1, "phase": phase, "beat": beat,
                  "narration": narration, "tool": tool, "args": args, "result": result})


async def session_readonly() -> None:
    async with stdio_client(_server(writes=False)) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            async def call(tool: str, args: dict | None = None) -> dict:
                return json.loads((await s.call_tool(tool, args or {})).content[0].text)

            r = await call("matter_health_report")
            record(
                "Morning triage", "insight",
                "User asks: “What needs attention across our matters this morning?” "
                "One tool call returns portfolio-level triage instead of six matter-by-matter reads.",
                "matter_health_report", {}, r)

            r = await call("get_deadlines")
            record(
                "Morning triage", "insight",
                "Follow-up: “What deadlines am I actually up against?” The deadline-chain engine "
                "derives dates the health report can't see — including a discovery meet-and-confer "
                "window that has ALREADY passed on Whitfield, and Hale's governmental notice date.",
                "get_deadlines", {}, r)

            r = await call("run_workflow", {"workflow_id": "sol-watchdog"})
            record(
                "Workflow preview", "dry-run",
                "“Run the SOL watchdog.” The engine defaults to a dry run: here is exactly what it "
                "WOULD do — which matters matched the 180-day window and every task/note it would "
                "create — before anything is touched.",
                "run_workflow", {"workflow_id": "sol-watchdog"}, r)

            r = await call("run_workflow", {"workflow_id": "stale-matter-sweep", "dry_run": False})
            record(
                "Workflow preview", "guardrail",
                "“Looks right — execute the stale-matter sweep for real.” REFUSED: the server is in "
                "read-only mode. An agent does not get write access to legal matter data by default; "
                "a human has to grant it out-of-band.",
                "run_workflow", {"workflow_id": "stale-matter-sweep", "dry_run": False}, r)


async def session_writes() -> None:
    record(
        "Human decision", "guardrail",
        "The operator — a human — restarts the server with FILEVINE_MCP_ALLOW_WRITES=1. "
        "Granting an agent write access to matters is an explicit, logged, out-of-band decision, "
        "not something the agent can talk its way into.",
        None, None, None)

    async with stdio_client(_server(writes=True)) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            async def call(tool: str, args: dict | None = None) -> dict:
                return json.loads((await s.call_tool(tool, args or {})).content[0].text)

            r = await call("run_workflow", {"workflow_id": "stale-matter-sweep", "dry_run": False})
            record(
                "Act", "action",
                "Same command, writes enabled: the sweep files reactivation tasks on every matter "
                "that has sat quiet past 21 days and stamps each with an explanatory note.",
                "run_workflow", {"workflow_id": "stale-matter-sweep", "dry_run": False}, r)

            # dates computed relative to today: fixtures anchor-shift keeps the
            # portfolio evergreen, so the demo must not hardcode calendar dates
            today = date.today()
            args = {"project_id": 10243,
                    "title": "Escalate: partner review of RFP Set 1 objections — meet-and-confer window passed",
                    "assignee": "D. Okafor", "due_date": (today + timedelta(days=2)).isoformat(),
                    "priority": "critical"}
            r = await call("create_task", args)
            record(
                "Act", "action",
                "Acting on the deadline finding: a well-scoped, critical task on Whitfield — the "
                "156-page RFP response has been unreviewed for 47 days and the meet-and-confer "
                "window already closed.",
                "create_task", args, r)

            served = (today - timedelta(days=47)).isoformat()
            closed = (today - timedelta(days=12)).isoformat()
            args = {"project_id": 10243,
                    "text": f"[triage] Meet-and-confer window on Defendant's RFP Set 1 responses "
                            f"(served {served}) closed {closed}. Escalation task filed to D. Okafor "
                            f"{today.isoformat()}; recommend serving deficiency letter with the "
                            f"meet-and-confer request to preserve the objection record."}
            r = await call("add_note", args)
            record(
                "Act", "action",
                "The matter file gets the context, not just the task — the next person who opens "
                "Whitfield sees why the escalation exists.",
                "add_note", args, r)

            r = await call("export_snapshot")
            record(
                "Extract", "action",
                "Finally: “Snapshot the org for the BI pipeline.” Four CSVs plus a manifest with "
                "row counts and a frozen column contract — a point-in-time extract in the spirit "
                "of DataBridge.",
                "export_snapshot", {}, r)


def audit_tail() -> None:
    lines = [json.loads(l) for l in AUDIT.read_text().splitlines() if l.strip()]
    record(
        "Prove it", "audit",
        f"Every one of the {len(lines)} calls this session — including the refused one — is in "
        "audit.jsonl with tool, arguments, mode, and timestamp. When a firm asks “what did the "
        "agent do to our matters?”, the answer is a file, not a shrug.",
        None, None, {"auditEntries": len(lines), "lastThree": lines[-3:]})


def write_markdown() -> None:
    md = ["# filevine-mcp — recorded demo session",
          f"\nRecorded {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')} against mock data "
          "(six fictional plaintiff-side matters). Every tool result below is the server's real "
          "output, captured over stdio by a scripted MCP client (`demo_agent.py`).\n"]
    for st in STEPS:
        md.append(f"\n---\n\n## Step {st['step']} — {st['phase']} · `{st['beat']}`\n")
        md.append(st["narration"] + "\n")
        if st["tool"]:
            md.append(f"**Tool:** `{st['tool']}`  \n**Args:** `{json.dumps(st['args'])}`\n")
        if st["result"] is not None:
            body = json.dumps(st["result"], indent=2)
            if len(body) > 2600:
                body = body[:2600] + "\n  ... (truncated; full output in transcript.json)"
            md.append(f"\n```json\n{body}\n```\n")
    (DEMO_DIR / "transcript.md").write_text("".join(md))


async def main() -> None:
    DEMO_DIR.mkdir(exist_ok=True)
    if AUDIT.exists():
        AUDIT.unlink()  # fresh audit trail so the final count is this session's
    await session_readonly()
    await session_writes()
    audit_tail()
    (DEMO_DIR / "transcript.json").write_text(json.dumps(
        {"recorded": datetime.now(timezone.utc).isoformat(),
         "mode": "mock", "steps": STEPS}, indent=2))
    write_markdown()
    print(f"Recorded {len(STEPS)} steps -> demo/transcript.json, demo/transcript.md")


if __name__ == "__main__":
    asyncio.run(main())
