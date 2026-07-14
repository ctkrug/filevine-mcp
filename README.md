# filevine-mcp — a Platform MCP beta candidate, built from the outside

A working MCP (Model Context Protocol) server for [Filevine](https://www.filevine.com),
plus the product package to ship it: PRD, beta program plan, working backlog, and release
notes. Built as an application work sample for the **PM II, API Platform** role — the
posting lists *LOIS Workflows, DataBridge, and Platform MCP* as the portfolio, so this kit
touches all three:

| Portfolio product | This kit's analog |
|---|---|
| **Platform MCP** | This server: 10 tools, scoped permissions, dry-run defaults, full audit trail |
| **LOIS Workflows** | `workflows.json` + `run_workflow`: a declarative workflow engine with preview-first execution and idempotency guards |
| **DataBridge** | `export_snapshot`: schema-versioned extracts with a manifest (CSV in miniature; production would hand off to real DataBridge/Snowflake) |

Built by [Charlie Krug](https://www.linkedin.com/in/charliekrug) · prototyped with Claude
Code — which is exactly the workflow this server exists to serve.

## Why these design choices (the PM part)

**Read-only by default.** Write tools (`create_task`, `add_note`, `run_workflow` with
`dry_run=false`) refuse to run unless the operator sets `FILEVINE_MCP_ALLOW_WRITES=1`. An
agent touching legal matter data should require an explicit human decision to get write
access — the same principle I use for my autonomous trading agents (hard-coded risk
controls, human-only arming).

**Preview before act.** `run_workflow` defaults to dry-run: exactly which matters matched
and every task/note it would create, before anything happens. Idempotency guards mean
re-running a workflow never duplicates open work.

**Every call is audited.** Tool, arguments, mode, timestamp → `audit.jsonl` — including
refused calls. When a firm asks "what did the agent do to our matters?", the answer is a
file, not a shrug.

**Insight, not just CRUD.** `matter_health_report` (portfolio triage) and `get_deadlines`
(rule-derived deadline chains — SOL, governmental notice windows, discovery
meet-and-confer clocks) surface what needs attention before anyone asks: the LOIS thesis,
reactive → proactive, expressed as MCP tools.

**Mock mode out of the box.** Six realistic fictional plaintiff-side matters, zero
credentials — which doubles as the self-serve sandbox Filevine's platform doesn't ship
today. Real credentials flip it to live mode via the *documented* auth flow (see below).

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install mcp   # Python 3.10+
.venv/bin/python test_smoke.py                        # 26 checks over stdio
.venv/bin/python demo_agent.py                        # records demo/transcript.{json,md}
```

Claude Code:

```bash
claude mcp add filevine -- /path/to/filevine-mcp/.venv/bin/python /path/to/filevine-mcp/server.py
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "filevine": {
      "command": "/path/to/filevine-mcp/.venv/bin/python",
      "args": ["/path/to/filevine-mcp/server.py"],
      "env": { "FILEVINE_MCP_ALLOW_WRITES": "0" }
    }
  }
}
```

Live mode (real org — untested, see honest scope notes):

```bash
export FILEVINE_CLIENT_ID=...      # Account Manager → Client Secrets
export FILEVINE_CLIENT_SECRET=...
export FILEVINE_PAT=...            # service-account Personal Access Token
export FILEVINE_REGION=us          # or ca
export FILEVINE_MCP_ALLOW_WRITES=1 # only if you mean it
```

## Tools

| Tool | What it does | Writes? |
|---|---|---|
| `search_projects` | Find matters by name/client, practice area, phase | no |
| `get_project` | Full matter snapshot: fields + docs + open tasks + notes | no |
| `list_documents` | Docs on a matter; filter to pending-review | no |
| `matter_health_report` | Portfolio triage: stale / overdue / stuck / SOL-window / unassigned | no |
| `get_deadlines` | Rule-derived deadline chains with severity + rule basis | no |
| `list_workflows` | The declarative workflow library | no |
| `run_workflow` | Dry-run preview by default; gated execution with idempotency guards | gated |
| `create_task` | File a validated, well-scoped task | gated |
| `add_note` | Append a matter note | gated |
| `export_snapshot` | Schema-versioned CSV extract + manifest (writes locally only) | no |

Resource: `filevine://health/summary` — one-paragraph standup summary.

## The recorded demo

`demo/transcript.md` is a full 10-step session captured over stdio by `demo_agent.py`
(a scripted MCP client — deterministic on purpose): morning triage → deadline chains →
workflow dry-run → **refused write in read-only mode** → human enables writes → workflow
executes → escalation task on the blown meet-and-confer window → snapshot export → audit
trail recap. Every tool result in it is real server output.

## The product package

`pm-package/` is the PM half of the work sample:

- **`PRD-platform-mcp-beta.md`** — problem, users (including the agent as a user), scope
  and deliberate non-goals, permission/audit model, success metrics, LEX-timed rollout,
  risks, and open questions for the Senior PM.
- **`beta-program-plan.md`** — cohort design (including inviting the unofficial-MCP
  maintainers), week-by-week arc, feedback→issue pipeline, exit AND kill criteria.
- **`backlog.md`** — 16 issues across 5 epics, each with user story + acceptance criteria.
- **`release-notes-draft.md`** — customer-facing announcement + internal enablement note.

## Honest scope notes

- **Live mode is written to Filevine's documented flow but untested against a real org** —
  I don't have credentials as an outside candidate, and there's no public sandbox. The
  documented flow (PAT token exchange at identity.filevine.com, `GetUserOrgsWithToken`
  bootstrap, `x-fv-orgid`/`x-fv-userid` headers, US/CA hosts) is implemented in
  `LiveBackend`; mock mode is the fully tested path (26 smoke checks, both permission modes).
- Deadline rules are illustrative (Colorado-flavored) to demonstrate the chain concept —
  not legal advice; a real product sources per-jurisdiction rulesets.
- Fixture data is invented; any resemblance to real parties is coincidental.
