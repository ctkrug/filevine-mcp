"""Smoke test: spins up server.py over stdio as a real MCP client and exercises every tool.

Run:  python3 test_smoke.py                       (read-only mode)
      FILEVINE_MCP_ALLOW_WRITES=1 python3 test_smoke.py   (writes enabled)
Exit 0 = all checks passed.
"""

import sys

if sys.version_info < (3, 10):
    sys.exit("test_smoke.py needs Python 3.10+ — run ./setup.sh (it finds one and builds the venv).")

import asyncio
import json
import os
import subprocess
import tempfile
from datetime import date, timedelta

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    sys.exit("The 'mcp' package isn't installed here — run ./setup.sh, then .venv/bin/python test_smoke.py")

EXPORT_TMP = tempfile.mkdtemp(prefix="fv-mcp-export-")
SERVER = StdioServerParameters(
    command=sys.executable,
    args=["server.py"],
    env={**os.environ,
         "FILEVINE_MCP_ALLOW_WRITES": os.environ.get("FILEVINE_MCP_ALLOW_WRITES", "0"),
         "FILEVINE_EXPORT_DIR": EXPORT_TMP},
)

ALL_TOOLS = {
    "search_projects", "get_project", "list_documents", "create_task", "add_note",
    "matter_health_report", "get_deadlines", "list_workflows", "run_workflow",
    "export_snapshot",
}


def check(label: str, cond: bool) -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        raise SystemExit(1)


async def main() -> None:
    writes = os.environ.get("FILEVINE_MCP_ALLOW_WRITES") == "1"

    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            async def call(tool: str, args: dict | None = None) -> dict:
                return json.loads((await s.call_tool(tool, args or {})).content[0].text)

            tools = {t.name for t in (await s.list_tools()).tools}
            check("all ten tools registered", tools == ALL_TOOLS)

            r = await call("search_projects", {"query": "alvarez"})
            check("search finds Alvarez matter", r["count"] == 1 and r["projects"][0]["projectId"] == 10241)

            r = await call("search_projects", {"phase": "Treatment"})
            check("phase filter returns 2 matters", r["count"] == 2)

            r = await call("search_projects", {"query": "zzz-no-such-client"})
            check("zero-result search returns a teaching hint", r["count"] == 0 and "hint" in r)

            r = await call("get_project", {"project_id": 10243})
            check("get_project returns docs+tasks+notes",
                  len(r["documents"]) == 2 and len(r["openTasks"]) == 2 and len(r["notes"]) == 1)

            r = await call("get_project", {"project_id": 99999})
            check("get_project unknown id -> error", "error" in r)

            r = await call("list_documents", {"project_id": 10241, "pending_review_only": True})
            check("pending-review filter works", r["count"] == 1 and "DemandLetter" in r["documents"][0]["filename"])

            r = await call("matter_health_report")
            check("health report: finds stale matters", any(x["projectId"] == 10243 for x in r["staleMatters"]))
            check("health report: finds overdue tasks", len(r["overdueTasks"]) >= 2)
            check("health report: flags Hale SOL window", any("Hale" in x["project"] for x in r["solWithin180Days"]))
            check("health report: flags unassigned Romero intake",
                  any("Romero" in x for x in r["unassignedMatters"]))

            # --- deadline chains -------------------------------------------------
            r = await call("get_deadlines")
            rules = {(d["project"], d["rule"]) for d in r["deadlines"]}
            check("deadlines: Hale governmental notice derived",
                  any("Hale" in p and "notice" in rule.lower() for p, rule in rules))
            check("deadlines: Whitfield meet-and-confer overdue", any(
                "Whitfield" in d["project"] and d["severity"] == "overdue" for d in r["deadlines"]))
            check("deadlines: sorted soonest-first",
                  [d["date"] for d in r["deadlines"]] == sorted(d["date"] for d in r["deadlines"]))
            check("deadlines: Hale SOL is exactly 81 days out (evergreen fixtures)", any(
                "Hale" in d["project"] and d["rule"] == "Statute of limitations"
                and d["daysRemaining"] == 81 for d in r["deadlines"]))
            check("deadlines: Romero cert-of-review pending trigger",
                  any("Romero" in u["project"] for u in r["notYetTriggered"]))
            r = await call("get_deadlines", {"project_id": 99999})
            check("deadlines unknown id -> error", "error" in r)

            # --- workflows -------------------------------------------------------
            r = await call("list_workflows")
            check("workflow library has 3 workflows", r["count"] == 3)

            r = await call("run_workflow", {"workflow_id": "nope"})
            check("unknown workflow -> error with suggestions", "error" in r and len(r["available"]) == 3)

            r = await call("run_workflow", {"workflow_id": "sol-watchdog"})
            check("sol-watchdog dry-run matches SOL-window matters",
                  r["dryRun"] and any("Hale" in m for m in r["matchedMatters"]))
            check("sol-watchdog plans critical tasks", any(
                a["type"] == "create_task" and a["priority"] == "critical" for a in r["plannedActions"]))

            r = await call("run_workflow", {"workflow_id": "intake-triage"})
            check("intake-triage idempotency guard skips existing assignment task",
                  any("idempotency" in s_["reason"] for s_ in r["skipped"]))

            r = await call("run_workflow", {"workflow_id": "stale-matter-sweep", "dry_run": False})
            check("live workflow gated by write flag" if not writes else "live workflow executes with writes on",
                  ("error" in r) != writes)
            if writes:
                check("live workflow reports executed actions", len(r["executedActions"]) >= 2)

            # --- writes gate -----------------------------------------------------
            due = (date.today() + timedelta(days=30)).isoformat()
            r = await call("create_task", {"project_id": 10241, "title": "t", "assignee": "paralegal.t",
                                           "due_date": due})
            check("create_task gated by write flag" if not writes else "create_task works with writes on",
                  ("error" in r) != writes)
            if writes:
                r = await call("create_task", {"project_id": 10241, "title": "t",
                                               "assignee": "Bob Nobody", "due_date": due})
                check("create_task refuses unknown assignee with a teaching error",
                      "error" in r and "Known people" in r["error"])

            # --- snapshot export -------------------------------------------------
            r = await call("export_snapshot")
            check("snapshot manifest lists 4 tables", len(r["tables"]) == 4)
            check("snapshot CSVs written to disk", all(
                os.path.exists(os.path.join(r["path"], t["file"])) for t in r["tables"]))
            check("snapshot row counts sane",
                  next(t["rows"] for t in r["tables"] if t["table"] == "projects") == 6)

            res = await s.read_resource("filevine://health/summary")
            check("health summary resource reads", "Portfolio health" in res.contents[0].text)

    # --- anchor-shift mechanism: the reason the demo is evergreen --------------
    # Every load shifts fixture dates by (today - anchor). Overriding the anchor to
    # 30 days ago must move every derived number by exactly +30 — proving relative
    # time is preserved on any future clone (where shift = today - real anchor).
    aged = StdioServerParameters(
        command=sys.executable, args=["server.py"],
        env={**os.environ, "FILEVINE_MCP_ALLOW_WRITES": "0", "FILEVINE_EXPORT_DIR": EXPORT_TMP,
             "FILEVINE_FIXTURE_ANCHOR": (date.today() - timedelta(days=30)).isoformat()},
    )
    async with stdio_client(aged) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            r = json.loads((await s.call_tool("get_deadlines", {})).content[0].text)
            check("anchor shift moves Hale SOL by exactly the delta (81 -> 111)", any(
                "Hale" in d["project"] and d["rule"] == "Statute of limitations"
                and d["daysRemaining"] == 111 for d in r["deadlines"]))
            r = json.loads((await s.call_tool("matter_health_report", {})).content[0].text)
            check("anchor shift keeps the RFP task overdue by 33-30=3 days", any(
                "RFP" in x["task"] and x["daysOverdue"] == 3 for x in r["overdueTasks"]))

    # --- onboarding helper -----------------------------------------------------
    out = subprocess.run([sys.executable, "setup_helper.py"], capture_output=True, text=True)
    check("setup_helper prints ready-to-paste connection config",
          out.returncode == 0 and "claude mcp add filevine" in out.stdout
          and "mcpServers" in out.stdout)

    print(f"\nAll smoke checks passed ({'writes-enabled' if writes else 'read-only'} mode).")


if __name__ == "__main__":
    asyncio.run(main())
