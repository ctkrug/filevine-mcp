# Platform MCP Beta — Working Backlog

16 issues across 5 epics, written the way I'd file them: user story, acceptance criteria,
size, priority. Sized S/M/L (≈ ≤2d / ≤1wk / >1wk of eng time). Issues reference the real
Filevine platform (PAT token exchange, org/user headers, scopes, US/CA environments,
existing audit infrastructure) — see `PRD-platform-mcp-beta.md` for context.

---

## Epic A — Auth & provisioning

**A1 · Mint MCP credentials from Account Manager** — `M` · `P0`
As an org admin, I can create a "Platform MCP" credential (backed by a service-account PAT
+ client pair) from Account Manager without emailing anyone, so connecting an agent is
self-serve.
- AC1: New credential type visible only to Account Admins; creation flow ≤ 3 steps.
- AC2: Credential is minted read-only; write scopes are unchecked by default and each one
  (`tasks:write`, `notes:write`, `workflows:execute`) requires an explicit toggle.
- AC3: Environment (US/CA) is pinned at mint time and displayed on the credential card.
- AC4: Revoking the credential kills active MCP sessions within 60s.
- AC5: Creation/revocation events appear in the org audit log.

**A2 · One-string connection setup** — `S` · `P0`
As a firm IT admin, I get a single copy-paste connection snippet (Claude Desktop JSON +
`claude mcp add` command) at credential creation, so setup doesn't require reading the
token-exchange docs.
- AC1: Snippet renders with credential ID pre-filled, secret redacted until reveal.
- AC2: Snippet works unmodified on Claude Desktop and Claude Code current versions.
- AC3: Docs page linked from the snippet; TTFTC instrumentation event fires on first
  successful tool call (see D3).

**A3 · Token exchange + identity bootstrap inside the server** — `M` · `P0`
As an integrator, the MCP server handles the PAT→bearer exchange, org/user resolution
(`GetUserOrgsWithToken`), refresh before expiry, and the `x-fv-orgid`/`x-fv-userid`
headers internally, so the 4-credential/3-header dance is invisible to the agent.
- AC1: Bearer refreshed ≥120s before expiry; zero auth-related tool failures in a 24h soak.
- AC2: Multi-org PATs: org must be explicitly selected at config time; server refuses
  ambiguous defaults with an actionable error.
- AC3: Auth failures surface as structured MCP errors distinguishing expired-PAT vs.
  revoked-secret vs. firewall/IP block (the current opaque-403 case).

**A4 · Credential-expiry early warning** — `S` · `P1`
As an org admin, I get a banner + email 30 days before the client secret's 1-year
non-renewable expiry, so the agent doesn't silently die.
- AC1: Warning at T-30/T-7/T-1; includes regeneration link and updated snippet.
- AC2: Post-expiry tool calls return a "credential expired" structured error, not a 500.

## Epic B — Tool surface

**B1 · Read core: search_projects / get_project / list_documents** — `M` · `P0`
As an agent user, I can search matters and pull a full matter snapshot (fields + docs +
open tasks + recent notes) in ≤2 calls, so common questions don't need 6 round-trips.
- AC1: Search filters: text (name/client), practice area, phase; paginated ≤50/page.
- AC2: Snapshot response ≤ 40KB for a 500-doc matter (doc list truncates with a
  continuation token; content never included).
- AC3: Custom-field values resolve through the ProjectTypes/sections selector model
  without the caller knowing selectors exist.
- AC4: Golden-transcript eval: 20 canned prompts against fixture org produce correct
  tool-call sequences on Claude and GPT current models (see D4).

**B2 · Insight: matter_health_report + get_deadlines** — `M` · `P0`
As an ops director, one call surfaces stale matters, overdue tasks, stuck documents, and
deadline chains (SOL, notice windows, discovery clocks), so triage is proactive.
- AC1: Health report over a 2,000-matter org returns < 5s (server-side aggregation, not
  N+1 project reads).
- AC2: Deadline rules are org-configurable data, not code; ship with a documented default
  set + disclaimer.
- AC3: Every derived deadline carries its rule basis so a human can check the math.

**B3 · Gated writes: create_task / add_note** — `S` · `P0`
As a supervising attorney, agents can file tasks/notes only when the org granted the
write scope, and every write is attributed to the MCP credential (not a human user).
- AC1: Write without scope → structured refusal naming the missing scope and who can
  grant it (teaching error, not a 403).
- AC2: Task inputs validated (real project, ISO date, known assignee, enum priority);
  invalid input NEVER silently drops fields — explicit field-level errors (this is a
  deliberate break from the API's current 200-with-dropped-fields behavior).
- AC3: Writes appear in matter activity feed labeled as agent actions.

**B4 · Workflows: list_workflows + run_workflow with dry-run default** — `L` · `P1`
As an ops manager, I can preview exactly what a workflow would do (matched matters, every
task/note) before executing, so automation is trustworthy.
- AC1: `run_workflow` defaults to dry-run; execution requires `dry_run=false` AND
  `workflows:execute` scope.
- AC2: Idempotency guards: re-running a workflow never duplicates open tasks.
- AC3: Execution routes through the LOIS Workflows engine if available (decision open
  with Senior PM — see PRD §9); MCP layer stays a thin adapter either way.
- AC4: Dry-run + execute pair emits a linked audit event chain.

**B5 · DataBridge handoff: describe_snapshot** — `S` · `P2`
As a data engineer, the agent can tell me what DataBridge exposes (schemas, views,
latency, region) and generate the Snowflake share request, so analytics questions route
to the right surface instead of hammering the REST API.
- AC1: Tool returns DATABRIDGE schema catalog + freshness SLA (10–20 min) + docs links.
- AC2: If org lacks DataBridge, returns the provisioning path, not an error.

## Epic C — Governance & audit

**C1 · MCP actions in the org audit log** — `M` · `P0`
As a managing partner, I can filter the org audit log to "agent actions" and see every
MCP call (including refusals) with tool, arguments, credential, and timestamp.
- AC1: Audit event schema versioned; includes dry-run flag for workflow calls.
- AC2: Refused calls (missing scope, invalid input) are logged with refusal reason.
- AC3: Audit write is synchronous with the action — an unlogged write is a failed write.

**C2 · Rate limiting for agent traffic** — `M` · `P1`
As Filevine platform eng, MCP traffic rides its own gateway bucket with agent-appropriate
limits, so a runaway agent can't starve a firm's UI or integrations.
- AC1: Separate bucket per MCP credential; standard `RateLimit-*` headers surfaced as
  structured tool errors with retry-after guidance the agent can obey.
- AC2: Burst profile tuned for agent patterns (bursty reads, rare writes) and documented
  publicly — no invisible tiers for this surface.

**C3 · PII/privilege guardrail review** — `M` · `P0`
As security/compliance, v1 tool responses exclude document content, SSNs/financial
account fields, and privileged-flagged notes, so agent context windows don't become
discovery liabilities.
- AC1: Field-exclusion list reviewed by security + one design-partner GC; enforced
  server-side (not by tool-description convention).
- AC2: Red-team pass: 25 adversarial prompts attempting exfiltration via tool composition;
  zero disallowed fields returned.

## Epic D — DX, docs & instrumentation

**D1 · Quickstart + reference docs on developer.filevine.io** — `M` · `P0`
As an integrator, a single quickstart takes me from credential to first tool call in
<10 min, with a server-rendered page agents can read (the current SPA docs are invisible
to LLM tooling).
- AC1: Quickstart tested by 3 external devs, cold, screen-recorded; median < 10 min.
- AC2: Tool schema reference auto-generated from server source; llms.txt published.
- AC3: Changelog page with RSS/email subscription — first entry is the beta itself.

**D2 · Fixture sandbox org** — `M` · `P1`
As a prospective integrator, I can run the server in mock mode against a bundled fixture
org (or a hosted demo org) without production credentials, so evaluation needs zero risk.
- AC1: Mock mode ships in the server package; parity checks keep fixtures aligned with
  live schemas in CI.
- AC2: Fixture org includes deadline/workflow edge cases (public-entity notice, unassigned
  intake, overdue discovery) so demos show the insight tools honestly.

**D3 · Beta telemetry: TTFTC + tool-level analytics** — `S` · `P0`
As the PM, I can see per-org time-to-first-successful-call, weekly-active connections,
tool call/error counts (in the existing in-app API Usage tool), so beta health is measured,
not vibes.
- AC1: Dashboard: TTFTC funnel, WAU by org, error rate by tool, top error classes.
- AC2: Weekly automated digest posted to the beta channel.

**D4 · Golden-transcript eval harness in CI** — `M` · `P1`
As eng+PM, every schema change runs a canned-prompt eval suite against current Claude/GPT
models, so tool-description regressions are caught before agents in the field feel them.
- AC1: 20 scenario transcripts; CI fails on tool-selection or argument regressions.
- AC2: Eval results attached to release PRs; PM reviews diffs as part of acceptance.

## Epic E — Beta ops

**E1 · Design-partner cohort recruitment & agreements** — `S` · `P0`
As the PM, 8–12 firms + 2–3 Certified Partners are enrolled with expectations set
(feedback cadence, data handling, non-GA disclaimer), so the beta produces signal.
- AC1: Cohort mix: ≥3 high-volume PI, ≥2 mid-size litigation, ≥1 gov-adjacent, ≥2 of the
  existing community MCP server maintainers invited.
- AC2: Signed beta terms; named champion + weekly office-hours slot per org.

**E2 · Feedback→issue synthesis pipeline** — `S` · `P0`
As the PM, all beta feedback (office hours, support tickets, telemetry anomalies) lands in
one triage queue and becomes labeled, prioritized issues within 48h, so early adopters see
their input reflected (and engineering never waits on product).
- AC1: Single intake form + support-ticket tag; weekly synthesis doc linking every issue
  to its evidence.
- AC2: Beta-blocking label SLA: triaged <24h, decision (fix/defer + why) communicated to
  the reporting firm <72h.
