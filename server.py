"""
filevine-mcp — an MCP server for Filevine's API.

Lets any MCP client (Claude Code, Claude Desktop, or an agent pipeline) search matters,
read documents/tasks/notes, file well-scoped tasks, and pull a cross-matter health report
in the spirit of LOIS: surfacing what needs attention before someone asks.

Covers all three product surfaces named in Filevine's API Platform portfolio:
  * LOIS Workflows  -> list_workflows / run_workflow: a declarative workflow engine
    (workflows.json) with dry-run previews, idempotency guards, and write-gated execution.
  * DataBridge      -> export_snapshot: a versioned, schema-stable CSV extract with a manifest.
  * Platform MCP    -> this server itself: the tool surface, permission model, and audit trail.

Design decisions (deliberate, and worth reading):
  * READ-ONLY BY DEFAULT. Write tools (create_task, add_note) refuse to run unless
    FILEVINE_MCP_ALLOW_WRITES=1. An agent touching legal matter data should need an
    explicit human decision to get write access.
  * EVERY CALL IS AUDITED. Tool name, arguments, mode, and timestamp are appended to
    audit.jsonl. If an agent did something to a matter, you can answer "what, when, why."
  * MOCK MODE OUT OF THE BOX. Runs against bundled fixture data (six realistic
    plaintiff-side matters) with zero credentials — doubling as the self-serve sandbox
    Filevine doesn't ship. Set FILEVINE_CLIENT_ID / FILEVINE_CLIENT_SECRET / FILEVINE_PAT
    to target a real org via the documented PAT token-exchange flow (see LiveBackend).

Built by Charlie Krug (github.com/ctkrug), prototyped with Claude Code — which is the
workflow the tool is for.
"""

from __future__ import annotations

import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

HERE = Path(__file__).parent
AUDIT_PATH = HERE / "audit.jsonl"
STALE_DAYS = 21  # a matter with no activity for 3 weeks is drifting
WORKFLOWS = json.loads((HERE / "workflows.json").read_text())["workflows"]
EXPORT_DIR = Path(os.environ.get("FILEVINE_EXPORT_DIR", HERE / "exports"))

mcp = FastMCP(
    "filevine",
    instructions=(
        "Filevine legal matter data. Read tools are always available; write tools "
        "(create_task, add_note, run_workflow with dry_run=false) work only when the "
        "operator has set FILEVINE_MCP_ALLOW_WRITES=1. run_workflow defaults to dry_run "
        "— always show the user the dry-run plan before executing. Matter data is "
        "sensitive: quote it precisely, never speculate about parties, and prefer "
        "matter_health_report / get_deadlines for portfolio-level questions."
    ),
)

# --------------------------------------------------------------------------- backend


class MockBackend:
    """Bundled fixture data - six plaintiff-side matters. No credentials needed."""

    mode = "mock"

    def __init__(self) -> None:
        self._db = json.loads((HERE / "fixtures.json").read_text())
        self._next_task_id = 9100
        self._next_note_id = 7100

    def projects(self) -> list[dict]:
        return self._db["projects"]

    def documents(self) -> list[dict]:
        return self._db["documents"]

    def tasks(self) -> list[dict]:
        return self._db["tasks"]

    def notes(self) -> list[dict]:
        return self._db["notes"]

    def create_task(self, project_id: int, title: str, assignee: str, due: str, priority: str) -> dict:
        self._next_task_id += 1
        task = {
            "taskId": self._next_task_id,
            "projectId": project_id,
            "title": title,
            "assignee": assignee,
            "dueDate": due,
            "status": "open",
            "priority": priority,
        }
        self._db["tasks"].append(task)
        return task

    def add_note(self, project_id: int, text: str) -> dict:
        self._next_note_id += 1
        note = {
            "noteId": self._next_note_id,
            "projectId": project_id,
            "authorId": "mcp-agent",
            "date": date.today().isoformat(),
            "text": text,
        }
        self._db["notes"].append(note)
        return note


class LiveBackend:
    """
    Real Filevine org via the flow their docs actually describe (developer.filevine.io +
    support.filevine.com API section), which is NOT a plain client-credentials grant:

      1. POST {identity}/connect/token  (form-encoded)
         grant_type=personal_access_token, client_id, client_secret, token=<PAT>,
         scope="fv.api.gateway.access tenant filevine.v2.api.* email openid fv.auth.tenant.read"
      2. POST {api}/fv-app/v2/utils/GetUserOrgsWithToken  (bearer)  -> userId + orgId
      3. Every request carries THREE headers: Authorization Bearer, x-fv-orgid, x-fv-userid.

    Env: FILEVINE_CLIENT_ID, FILEVINE_CLIENT_SECRET, FILEVINE_PAT,
         FILEVINE_REGION=us|ca (default us), FILEVINE_ORG_ID (optional override).
    NOTE: written to the documented flow, but untested against a real org — I don't have
    credentials as an outside candidate, and Filevine offers no self-serve sandbox (mock
    mode is this repo's stand-in for one). Bootstrap parsing is deliberately defensive.
    This class is the seam where reality would be reconciled.
    """

    mode = "live"
    HOSTS = {
        "us": ("https://identity.filevine.com", "https://api.filevineapp.com"),
        "ca": ("https://identity.filevine.ca", "https://api.filevineapp.ca"),
    }
    SCOPES = "fv.api.gateway.access tenant filevine.v2.api.* email openid fv.auth.tenant.read"

    def __init__(self) -> None:
        identity, api = self.HOSTS[os.environ.get("FILEVINE_REGION", "us")]
        self._token_url = f"{identity}/connect/token"
        self._base = os.environ.get("FILEVINE_BASE_URL", f"{api}/fv-app/v2")
        self._client_id = os.environ["FILEVINE_CLIENT_ID"]
        self._client_secret = os.environ["FILEVINE_CLIENT_SECRET"]
        self._pat = os.environ["FILEVINE_PAT"]
        self._token: str | None = None
        self._token_exp = 0.0
        self._org_id = os.environ.get("FILEVINE_ORG_ID", "")
        self._user_id = ""

    # -- auth ---------------------------------------------------------------
    def _bearer(self) -> str:
        if self._token is None or time.time() > self._token_exp - 120:
            body = urllib.parse.urlencode(
                {
                    "grant_type": "personal_access_token",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "token": self._pat,
                    "scope": self.SCOPES,
                }
            ).encode()
            req = urllib.request.Request(
                self._token_url, data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                tok = json.loads(r.read())
            self._token = tok["access_token"]
            self._token_exp = time.time() + int(tok.get("expires_in", 3600))
            self._bootstrap_identity()
        return self._token

    def _bootstrap_identity(self) -> None:
        """Resolve userId/orgId once per token; every v2 call must carry both as headers."""
        req = urllib.request.Request(
            f"{self._base}/utils/GetUserOrgsWithToken", data=b"{}", method="POST",
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        self._user_id = str(data.get("userId") or data.get("user", {}).get("userId") or self._user_id)
        if not self._org_id:
            orgs = data.get("orgs") or data.get("organizations") or []
            if orgs:
                first = orgs[0]
                self._org_id = str(first.get("orgId") or first.get("id") or "")

    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "Authorization": f"Bearer {self._bearer()}",
            "x-fv-orgid": self._org_id,
            "x-fv-userid": self._user_id,
        }
        return {**h, **(extra or {})}

    def _get(self, path: str, params: dict | None = None) -> dict:
        qs = f"?{urllib.parse.urlencode(params)}" if params else ""
        req = urllib.request.Request(f"{self._base}{path}{qs}", headers=self._headers())
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self._base}{path}",
            data=json.dumps(payload).encode(),
            headers=self._headers({"Content-Type": "application/json"}),
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    # -- resources (paths per Filevine v2 docs; see class docstring) --------
    def projects(self) -> list[dict]:
        return self._get("/projects", {"limit": 100}).get("items", [])

    def documents(self) -> list[dict]:
        return self._get("/documents", {"limit": 100}).get("items", [])

    def tasks(self) -> list[dict]:
        return self._get("/tasks", {"limit": 100}).get("items", [])

    def notes(self) -> list[dict]:
        return self._get("/notes", {"limit": 100}).get("items", [])

    def create_task(self, project_id: int, title: str, assignee: str, due: str, priority: str) -> dict:
        return self._post("/tasks", {
            "projectId": project_id, "title": title,
            "assignee": assignee, "dueDate": due, "priority": priority,
        })

    def add_note(self, project_id: int, text: str) -> dict:
        return self._post("/notes", {"projectId": project_id, "text": text})


BACKEND = (
    LiveBackend()
    if all(os.environ.get(k) for k in ("FILEVINE_CLIENT_ID", "FILEVINE_CLIENT_SECRET", "FILEVINE_PAT"))
    else MockBackend()
)
WRITES_ENABLED = os.environ.get("FILEVINE_MCP_ALLOW_WRITES") == "1"


# --------------------------------------------------------------------------- helpers


def _audit(tool: str, args: dict) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "args": args,
        "mode": BACKEND.mode,
        "writes_enabled": WRITES_ENABLED,
    }
    with AUDIT_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _days_since(iso: str) -> int:
    return (date.today() - date.fromisoformat(iso)).days


def _project_or_error(project_id: int) -> dict | None:
    return next((p for p in BACKEND.projects() if p["projectId"] == project_id), None)


WRITE_DISABLED_MSG = (
    "Write tools are disabled (read-only mode). The operator must set "
    "FILEVINE_MCP_ALLOW_WRITES=1 to enable task/note creation. This is deliberate: "
    "agents should not modify legal matter data without an explicit human decision."
)


# ----------------------------------------------------------------------------- tools


@mcp.tool()
def search_projects(query: str = "", practice_area: str = "", phase: str = "") -> str:
    """Search matters by name/client (query), practice area, and/or phase
    (Intake, Treatment, Demand, Litigation, Settlement). Empty filters match all."""
    _audit("search_projects", {"query": query, "practice_area": practice_area, "phase": phase})
    q = query.lower()
    hits = [
        p for p in BACKEND.projects()
        if (not q or q in p["projectName"].lower() or q in p["clientName"].lower())
        and (not practice_area or practice_area.lower() in p["practiceArea"].lower())
        and (not phase or phase.lower() == p["phase"].lower())
    ]
    return json.dumps({"count": len(hits), "projects": hits}, indent=2)


@mcp.tool()
def get_project(project_id: int) -> str:
    """Full snapshot of one matter: core fields plus its documents, open tasks, and notes."""
    _audit("get_project", {"project_id": project_id})
    proj = _project_or_error(project_id)
    if proj is None:
        return json.dumps({"error": f"No project with id {project_id}"})
    return json.dumps(
        {
            "project": proj,
            "daysSinceActivity": _days_since(proj["lastActivity"]),
            "documents": [d for d in BACKEND.documents() if d["projectId"] == project_id],
            "openTasks": [t for t in BACKEND.tasks() if t["projectId"] == project_id and t["status"] == "open"],
            "notes": [n for n in BACKEND.notes() if n["projectId"] == project_id],
        },
        indent=2,
    )


@mcp.tool()
def list_documents(project_id: int, pending_review_only: bool = False) -> str:
    """Documents on a matter, optionally only those awaiting review."""
    _audit("list_documents", {"project_id": project_id, "pending_review_only": pending_review_only})
    docs = [d for d in BACKEND.documents() if d["projectId"] == project_id]
    if pending_review_only:
        docs = [d for d in docs if d["reviewStatus"] == "pending_review"]
    return json.dumps({"count": len(docs), "documents": docs}, indent=2)


@mcp.tool()
def create_task(project_id: int, title: str, assignee: str, due_date: str, priority: str = "medium") -> str:
    """Create a task on a matter (due_date ISO YYYY-MM-DD; priority low|medium|high|critical).
    Requires writes to be enabled by the operator."""
    _audit("create_task", {"project_id": project_id, "title": title, "assignee": assignee,
                           "due_date": due_date, "priority": priority})
    if not WRITES_ENABLED:
        return json.dumps({"error": WRITE_DISABLED_MSG})
    if _project_or_error(project_id) is None:
        return json.dumps({"error": f"No project with id {project_id}"})
    try:
        date.fromisoformat(due_date)
    except ValueError:
        return json.dumps({"error": f"due_date must be ISO YYYY-MM-DD, got {due_date!r}"})
    if priority not in ("low", "medium", "high", "critical"):
        return json.dumps({"error": "priority must be low|medium|high|critical"})
    return json.dumps({"created": BACKEND.create_task(project_id, title, assignee, due_date, priority)}, indent=2)


@mcp.tool()
def add_note(project_id: int, text: str) -> str:
    """Append a note to a matter. Requires writes to be enabled by the operator."""
    _audit("add_note", {"project_id": project_id, "text": text[:200]})
    if not WRITES_ENABLED:
        return json.dumps({"error": WRITE_DISABLED_MSG})
    if _project_or_error(project_id) is None:
        return json.dumps({"error": f"No project with id {project_id}"})
    return json.dumps({"created": BACKEND.add_note(project_id, text)}, indent=2)


@mcp.tool()
def matter_health_report() -> str:
    """Portfolio-level triage: stale matters (no activity > 21 days), overdue open tasks,
    documents stuck in review, and statute-of-limitations dates inside 180 days.
    The 'what needs attention before someone asks' view."""
    _audit("matter_health_report", {})
    today = date.today()
    projects = {p["projectId"]: p for p in BACKEND.projects()}

    stale = [
        {"project": p["projectName"], "projectId": pid, "daysSinceActivity": _days_since(p["lastActivity"]),
         "phase": p["phase"], "leadAttorney": p["leadAttorney"]}
        for pid, p in projects.items() if _days_since(p["lastActivity"]) > STALE_DAYS
    ]
    overdue = [
        {"project": projects[t["projectId"]]["projectName"], "task": t["title"], "assignee": t["assignee"],
         "dueDate": t["dueDate"], "daysOverdue": (today - date.fromisoformat(t["dueDate"])).days,
         "priority": t["priority"]}
        for t in BACKEND.tasks()
        if t["status"] == "open" and date.fromisoformat(t["dueDate"]) < today
    ]
    stuck_docs = [
        {"project": projects[d["projectId"]]["projectName"], "filename": d["filename"],
         "daysInReview": _days_since(d["uploadedDate"])}
        for d in BACKEND.documents()
        if d["reviewStatus"] == "pending_review" and _days_since(d["uploadedDate"]) > 7
    ]
    sol_soon = [
        {"project": p["projectName"], "solDate": p["sol_date"],
         "daysRemaining": (date.fromisoformat(p["sol_date"]) - today).days}
        for p in projects.values()
        if 0 <= (date.fromisoformat(p["sol_date"]) - today).days <= 180
    ]

    return json.dumps(
        {
            "generated": today.isoformat(),
            "staleMatters": sorted(stale, key=lambda x: -x["daysSinceActivity"]),
            "overdueTasks": sorted(overdue, key=lambda x: -x["daysOverdue"]),
            "documentsStuckInReview": sorted(stuck_docs, key=lambda x: -x["daysInReview"]),
            "solWithin180Days": sorted(sol_soon, key=lambda x: x["daysRemaining"]),
            "unassignedMatters": [p["projectName"] for p in projects.values() if p["leadAttorney"] == "unassigned"],
        },
        indent=2,
    )


# ----------------------------------------------------------- deadline chain engine

DEADLINE_DISCLAIMER = (
    "Illustrative, Colorado-flavored ruleset to demonstrate deadline chains — not legal "
    "advice. A production implementation would source per-jurisdiction rules and let "
    "firms configure their own."
)


def _deadline_entries(p: dict) -> tuple[list[dict], list[dict]]:
    """Rule-based deadline chain for one matter -> (triggered, untriggered)."""
    today = date.today()
    docs = [d for d in BACKEND.documents() if d["projectId"] == p["projectId"]]
    out: list[dict] = []
    pending: list[dict] = []

    def add(rule: str, basis: str, when: date) -> None:
        days = (when - today).days
        severity = ("overdue" if days < 0 else "critical" if days <= 30
                    else "high" if days <= 90 else "medium" if days <= 180 else "low")
        out.append({"projectId": p["projectId"], "project": p["projectName"], "rule": rule,
                    "basis": basis, "date": when.isoformat(), "daysRemaining": days,
                    "severity": severity})

    add("Statute of limitations", "Matter SOL date on file", date.fromisoformat(p["sol_date"]))

    if "public entity" in p["practiceArea"].lower():
        add("Governmental notice of claim",
            "CGIA-style 182-day notice from incident date",
            date.fromisoformat(p["incidentDate"]) + timedelta(days=182))

    if p["phase"] == "Demand":
        demands = [d for d in docs if d["docType"] == "Demand Letter"]
        if demands:
            latest = max(demands, key=lambda d: d["uploadedDate"])
            add("Demand response follow-up",
                f"30-day insurer response window from latest demand doc ({latest['filename']})",
                date.fromisoformat(latest["uploadedDate"]) + timedelta(days=30))

    for d in docs:
        if d["docType"] == "Discovery" and d["reviewStatus"] == "pending_review":
            add("Discovery meet-and-confer window",
                f"35 days from service of responses ({d['filename']})",
                date.fromisoformat(d["uploadedDate"]) + timedelta(days=35))

    if p["phase"] == "Settlement":
        agreements = [d for d in docs if d["docType"] == "Settlement"]
        if agreements:
            latest = max(agreements, key=lambda d: d["uploadedDate"])
            add("Settlement disbursement clock",
                f"21-day funding/disbursement window from agreement draft ({latest['filename']})",
                date.fromisoformat(latest["uploadedDate"]) + timedelta(days=21))

    if "medical malpractice" in p["practiceArea"].lower() and p["phase"] in ("Intake", "Treatment"):
        pending.append({"projectId": p["projectId"], "project": p["projectName"],
                        "rule": "Certificate of review",
                        "basis": "Due 60 days after service of complaint (CRS 13-20-602-style)",
                        "triggersWhen": "complaint is filed and served"})

    return out, pending


@mcp.tool()
def get_deadlines(project_id: int = 0) -> str:
    """Rule-derived deadline chain: SOL, governmental notice windows, discovery
    meet-and-confer clocks, demand/settlement follow-ups. project_id=0 scans the whole
    portfolio. Sorted soonest-first with severity (overdue|critical|high|medium|low)."""
    _audit("get_deadlines", {"project_id": project_id})
    projects = BACKEND.projects()
    if project_id:
        projects = [p for p in projects if p["projectId"] == project_id]
        if not projects:
            return json.dumps({"error": f"No project with id {project_id}"})
    triggered: list[dict] = []
    untriggered: list[dict] = []
    for p in projects:
        t, u = _deadline_entries(p)
        triggered += t
        untriggered += u
    triggered.sort(key=lambda x: x["date"])
    return json.dumps({"generated": date.today().isoformat(),
                       "disclaimer": DEADLINE_DISCLAIMER,
                       "deadlines": triggered,
                       "notYetTriggered": untriggered}, indent=2)


# ------------------------------------------------------------------ workflow engine

_OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
}


class _SafeCtx(dict):
    def __missing__(self, key: str) -> str:  # leave unknown {placeholders} visible
        return "{" + key + "}"


def _wf_context(p: dict) -> _SafeCtx:
    today = date.today()
    ctx = _SafeCtx(p)
    ctx["days_to_sol"] = (date.fromisoformat(p["sol_date"]) - today).days
    ctx["days_since_activity"] = _days_since(p["lastActivity"])
    ctx["days_since_opened"] = _days_since(p["openedDate"])
    return ctx


def _wf_cond(cond: dict, ctx: dict) -> bool:
    return _OPS[cond["op"]](ctx.get(cond["field"]), cond["value"])


@mcp.tool()
def list_workflows() -> str:
    """The workflow library: id, name, description, conditions, and actions for each
    declarative workflow available to run_workflow."""
    _audit("list_workflows", {})
    return json.dumps({"count": len(WORKFLOWS), "workflows": WORKFLOWS}, indent=2)


@mcp.tool()
def run_workflow(workflow_id: str, dry_run: bool = True) -> str:
    """Run a declarative workflow from the library over every matter. DEFAULTS TO DRY RUN:
    returns the exact actions it would take without taking them. Executing for real needs
    dry_run=false AND writes enabled by the operator. Idempotent: actions carrying a
    skip_if_open_task_contains guard are skipped when a matching open task exists."""
    _audit("run_workflow", {"workflow_id": workflow_id, "dry_run": dry_run})
    wf = next((w for w in WORKFLOWS if w["workflowId"] == workflow_id), None)
    if wf is None:
        return json.dumps({"error": f"No workflow {workflow_id!r}. Use list_workflows.",
                           "available": [w["workflowId"] for w in WORKFLOWS]})
    if not dry_run and not WRITES_ENABLED:
        return json.dumps({"error": WRITE_DISABLED_MSG, "hint": "Re-run with dry_run=true to preview."})

    today = date.today()
    planned: list[dict] = []
    skipped: list[dict] = []
    matched: list[str] = []

    for p in BACKEND.projects():
        ctx = _wf_context(p)
        if not all(_wf_cond(c, ctx) for c in wf["conditions"]):
            continue
        matched.append(p["projectName"])
        open_titles = [t["title"] for t in BACKEND.tasks()
                       if t["projectId"] == p["projectId"] and t["status"] == "open"]
        for action in wf["actions"]:
            if "only_if" in action and not _wf_cond(action["only_if"], ctx):
                skipped.append({"project": p["projectName"], "action": action["type"],
                                "reason": f"only_if condition not met ({action['only_if']['field']})"})
                continue
            guard = action.get("skip_if_open_task_contains")
            if guard and any(guard.lower() in t.lower() for t in open_titles):
                skipped.append({"project": p["projectName"], "action": action["type"],
                                "reason": f"idempotency guard: open task already matches {guard!r}"})
                continue
            if action["type"] == "create_task":
                planned.append({"type": "create_task", "projectId": p["projectId"],
                                "project": p["projectName"],
                                "title": action["title"].format_map(ctx),
                                "assignee": action["assignee"].format_map(ctx),
                                "dueDate": (today + timedelta(days=action["due_in_days"])).isoformat(),
                                "priority": action["priority"]})
            elif action["type"] == "add_note":
                planned.append({"type": "add_note", "projectId": p["projectId"],
                                "project": p["projectName"],
                                "text": action["text"].format_map(ctx)})

    if dry_run:
        return json.dumps({"workflow": wf["name"], "dryRun": True,
                           "matchedMatters": matched, "plannedActions": planned,
                           "skipped": skipped}, indent=2)

    executed: list[dict] = []
    for a in planned:
        if a["type"] == "create_task":
            executed.append(BACKEND.create_task(a["projectId"], a["title"], a["assignee"],
                                                a["dueDate"], a["priority"]))
        else:
            executed.append(BACKEND.add_note(a["projectId"], a["text"]))
    return json.dumps({"workflow": wf["name"], "dryRun": False,
                       "matchedMatters": matched, "executedActions": executed,
                       "skipped": skipped}, indent=2)


# ----------------------------------------------------------------- snapshot exports

SNAPSHOT_SCHEMAS = {
    "projects": ["projectId", "projectName", "clientName", "practiceArea", "phase",
                 "incidentDate", "openedDate", "lastActivity", "leadAttorney", "sol_date",
                 "estValue"],
    "tasks": ["taskId", "projectId", "title", "assignee", "dueDate", "status", "priority"],
    "documents": ["documentId", "projectId", "filename", "docType", "uploadedDate",
                  "reviewStatus", "pages"],
    "notes": ["noteId", "projectId", "authorId", "date", "text"],
}


@mcp.tool()
def export_snapshot() -> str:
    """Versioned point-in-time extract of the org (projects, tasks, documents, notes) as
    CSVs with a manifest — a stable schema contract for BI/warehouse pipelines, in the
    spirit of DataBridge. Writes locally only; returns the manifest."""
    _audit("export_snapshot", {})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = EXPORT_DIR / f"snapshot-{stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    tables = {"projects": BACKEND.projects(), "tasks": BACKEND.tasks(),
              "documents": BACKEND.documents(), "notes": BACKEND.notes()}
    manifest = {"generated": datetime.now(timezone.utc).isoformat(), "mode": BACKEND.mode,
                "schemaVersion": "1.0", "path": str(dest), "tables": []}
    for name, rows in tables.items():
        cols = SNAPSHOT_SCHEMAS[name]
        with (dest / f"{name}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        manifest["tables"].append({"table": name, "file": f"{name}.csv",
                                   "rows": len(rows), "columns": cols})
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return json.dumps(manifest, indent=2)


# ------------------------------------------------------------------------- resources


@mcp.resource("filevine://health/summary")
def health_summary() -> str:
    """One-paragraph plain-text portfolio summary, suitable for a morning standup."""
    report = json.loads(matter_health_report())
    return (
        f"Portfolio health {report['generated']}: "
        f"{len(report['staleMatters'])} stale matter(s), "
        f"{len(report['overdueTasks'])} overdue task(s), "
        f"{len(report['documentsStuckInReview'])} document(s) stuck in review, "
        f"{len(report['solWithin180Days'])} SOL/notice deadline(s) within 180 days, "
        f"{len(report['unassignedMatters'])} unassigned matter(s)."
    )


if __name__ == "__main__":
    mcp.run()
