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
Code — which is exactly the workflow this server exists to serve. Watch the recorded demo
and read the full PM package at **[charliekrug.com/filevine](https://charliekrug.com/filevine)**.

## Why these design choices (the PM part)

**Read-only by default.** Write tools (`create_task`, `add_note`, `run_workflow` with
`dry_run=false`) refuse to run until a human grants writes (`./connect.sh --writes`, or
`FILEVINE_MCP_ALLOW_WRITES=1`). The gate isn't there to stop the *user* — a human can
always grant writes, in five seconds. It separates human authority from agent capability:
the switch lives outside the conversation, so no prompt — and no prompt injection buried in
matter data — can flip it, and every write in the audit trail traces back to a person and a
timestamp. A wrong answer is recoverable; a wrong write is in the matter file. (In
production this becomes per-scope credentials from the org admin, then an OAuth 2.1 consent
screen at GA — see the PRD.)

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
credentials — which doubles as a self-serve sandbox: the whole surface is evaluable
without an org. Real credentials flip it to live mode via the *documented* auth flow (see below).

**Evergreen fixtures.** Every date in the fixtures (fields *and* dates inside note text)
shifts by `today − anchor` at load: Whitfield is always 46 days stale, Hale's SOL is
always 81 days out, the blown meet-and-confer window always closed 12 days ago — clone
this repo six months from now and the demo reads exactly the same. The smoke suite
proves the mechanism (see the anchor-shift checks).

## Quickstart (macOS / Linux)

Four commands, no terminal experience needed. Open **Terminal** (⌘-space, type
"Terminal", return) and paste one line at a time:

```bash
git clone https://github.com/ctkrug/filevine-mcp && cd filevine-mcp
./setup.sh      # builds a private .venv, then proves it: all 31 smoke checks run before your eyes
./connect.sh    # registers the server with Claude Code (writes off) — or prints config for other clients
claude          # start Claude Code in this folder, then just ask about your matters
```

First question to try: *"What needs attention across our matters this morning?"* Then
*"Run the SOL watchdog workflow"* — and when you tell it to execute for real, watch it
**refuse**: the read-only default at work. Granting writes is one command — `./connect.sh
--writes` — deliberately a human step, never something the agent can talk its way into.
Everything runs on bundled fictional data; no credentials, and nothing installs outside
this folder.

First time using `git`? macOS will pop a dialog offering to install its developer
tools — click Install, let it finish, and run the command again.

The deeper pass, for reviewers who want the full confidence story:

```bash
.venv/bin/python setup_helper.py    # ready-to-paste config for Claude Desktop, Cursor, any MCP client
.venv/bin/python demo_agent.py      # re-records demo/transcript.{json,md} live
./verify.sh                         # full confidence check: cold clone + smoke + evergreen + live-failure
```

`verify.sh` is the "safe to show someone" gate. It runs four checks and only exits
green if all pass: (1) a **cold clone** of the committed tree builds from zero in a temp
dir — catching "works on my machine" and anything uncommitted; (2) the full **smoke**
suite; (3) **evergreen** — time-travels the demo across dates spanning years (plus a leap
day) and asserts every relative number is identical, proving a reviewer who clones this
months from now sees the exact same demo; (4) **live failure** — points live mode at a
dead host and bad config and asserts every failure is a clean, actionable message rather
than a stack trace. The clock is injected via `FILEVINE_TODAY` (see `_today()` in
`server.py`), which is how date-dependent behaviour is tested deterministically instead of
hoping today's date happens to line up.

`setup.sh` exists because macOS ships Python 3.9 as `python3` and the `mcp` package
needs 3.10+ — the #1 way a cold clone fails. `setup_helper.py` prints the exact
`claude mcp add` command, Claude Desktop JSON, generic MCP-client config, and an
MCP Inspector one-liner with absolute paths already filled in (backlog issue A2,
practiced on itself).

**Windows** (untested by the author — no Windows machine; these are the standard equivalents):

```powershell
py -3 -m venv .venv
.venv\Scripts\pip install mcp
.venv\Scripts\python test_smoke.py
.venv\Scripts\python setup_helper.py
```

**No Claude account handy?** Poke the tools from a browser with the official
inspector (needs Node): `npx @modelcontextprotocol/inspector .venv/bin/python server.py`
— or use any MCP client (Cursor, custom agents): command `.venv/bin/python`,
args `[server.py]`. One-off alternative if you use `uv`: `uv run --with mcp python server.py`.

Live mode (real org — written to the documented flow, untested against a real org; see honest scope notes):

```bash
export FILEVINE_CLIENT_ID=...      # Account Manager → Client Secrets
export FILEVINE_CLIENT_SECRET=...
export FILEVINE_PAT=...            # service-account Personal Access Token
export FILEVINE_REGION=us          # or ca
export FILEVINE_MCP_ALLOW_WRITES=1 # only if you mean it
```

All three of `CLIENT_ID / CLIENT_SECRET / PAT` switch it to live mode; set only some and it
**warns and stays in mock mode** rather than silently half-configuring. Auth is lazy — the
first tool call does the token exchange. **Because the flow is unverified against a real org,
every live failure is engineered to be legible, not a crash:** an auth rejection, an
unreachable host, an unexpected response shape, or a bad region all come back as a clean
`{"error": "..."}` with a specific cause and the reminder that mock mode needs no credentials
(e.g. `Filevine token exchange failed: HTTP 401 Unauthorized — the PAT or client credentials
are invalid or expired. (Unset FILEVINE_* to fall back to mock mode.)`). Transient server
errors (429/502/503/504) get one automatic retry. The whole failure surface is covered by
`test_live_failure.py` (Gate 4 of `./verify.sh`), which drives it offline against a dead host.
On-prem/staging hosts: override `FILEVINE_TOKEN_URL` and `FILEVINE_BASE_URL`.

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

## Troubleshooting (the live-on-a-call checklist)

- **`ModuleNotFoundError: No module named 'mcp'` or a version complaint** → you ran the
  system Python. Run `./setup.sh` once, then always use `.venv/bin/python`. Both entry
  points now exit with exactly this instruction instead of a stack trace.
- **Claude shows "failed to connect" for the server** → the configured command probably
  points at the wrong Python. Re-run `./connect.sh` from the repo folder (it re-registers
  with the right absolute paths), or run `.venv/bin/python setup_helper.py` and paste its
  output verbatim; for Claude Desktop, fully quit and reopen the app after editing the config.
- **Agent says it can't create tasks** → that's the read-only default working. Re-run
  `./connect.sh --writes` (or set `FILEVINE_MCP_ALLOW_WRITES=1` in the server's env block
  and reconnect) — deliberately a human step.
- **"Unknown assignee"** → tasks must land on a real desk; the error lists the org's
  known people (mock org: D. Okafor, S. Brandt, paralegal.t, paralegal.m, intake.desk).
- **Numbers don't match the recorded transcript exactly** → the recorded transcript is a
  point-in-time capture; live runs re-derive from the evergreen fixtures, so the *day
  counts* (46 stale, 81 to SOL, −12 meet-and-confer) always match even when calendar
  dates differ.
- **Mock state resets when the server restarts** → by design: the org is rebuilt from
  fixtures per process, so every demo starts clean. Created tasks/notes persist for the
  life of the session only. The audit trail (`audit.jsonl`) does persist across restarts.

## Honest scope notes

- **Live mode is written to Filevine's documented flow but untested against a real org** —
  I don't have credentials as an outside candidate, and there's no public sandbox. The
  documented flow (PAT token exchange at identity.filevine.com, `GetUserOrgsWithToken`
  bootstrap, `x-fv-orgid`/`x-fv-userid` headers, US/CA hosts) is implemented in
  `LiveBackend`; mock mode is the fully tested path (31 smoke checks read-only, 33 with
  writes). Live mode fails soft by design: unrecognized field shapes are normalized where
  possible and skipped-and-reported (`dataGaps`) where not — never guessed.
- Deadline rules are illustrative (Colorado-flavored) to demonstrate the chain concept —
  not legal advice; a real product sources per-jurisdiction rulesets.
- Fixture data is invented; any resemblance to real parties is coincidental.
