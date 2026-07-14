# PRD — Filevine Platform MCP, Private Beta

| | |
|---|---|
| **Status** | Draft for review — written as a work sample by an outside candidate |
| **Author** | Charlie Krug |
| **Date** | 2026-07-13 |
| **Reviewers** | Senior PM, API Platform (primary) · Eng lead · Security · Support enablement |
| **Working demo** | `../server.py` — a 10-tool reference implementation of this spec, runnable today |

> **Honest framing:** I don't have access to Filevine's internal architecture, roadmap, or
> the real Platform MCP plans. This is what I could construct from public signal (developer
> docs, support articles, LEX Summit coverage, community repos) — the version of this
> document I'd write in week two of the job would be better-informed. Treat it as a work
> sample: how I scope, what I check, where I put the guardrails.

## 1. Problem

Agents are becoming the primary new consumer of the Filevine API — and today they have no
sanctioned front door.

- **LOIS Console** (launched 2026-06-02) gives firms Filevine-built agents *inside* the
  platform. But firms and partners are also building agents *outside* it — in Claude,
  ChatGPT, custom pipelines — and those agents reach Filevine through whatever wrapper
  someone glued together.
- **The community has already voted.** At least three unofficial Filevine MCP servers exist
  (Advocate Cloud Solutions, Oktopeak, Rosen Advertising) plus Zapier's generic MCP surface.
  Demand is proven. Every one of them holds org credentials outside Filevine's control, with
  no Filevine-governed permission model, no audit trail a managing partner can pull, and no
  versioning contract.
- **The buyer's first question is governance.** Law firms ask "what can the agent touch, and
  what did it do?" before they ask anything else. An unofficial wrapper can't answer;
  the platform can.

A first-party MCP server converts an ungoverned integration pattern into a product surface
Filevine controls — and makes every MCP-speaking assistant a distribution channel.

## 2. Users

1. **Firm ops / IT admin (the governance buyer).** Decides whether any agent gets org
   credentials. Needs: scoped permissions, read-only default, an audit answer, revocation.
2. **Integration partner / consultancy developer.** Builds firm-specific automations today
   via REST + webhooks. Needs: stable tool schemas, sandbox data, error clarity, changelog.
3. **Ops director / paralegal supervisor (end beneficiary).** Never sees MCP; sees "our
   assistant catches the stale matters and the deadline no one calendared."
4. **The agent itself.** Tool descriptions, error messages, and result shapes are its UX.
   If a tool result confuses a model, that's a product defect on par with a broken screen.

## 3. Goals / non-goals

**V1 beta goals**

1. An org admin can provision a scoped MCP credential and connect Claude (Code/Desktop) to
   their org in under 10 minutes without contacting support.
2. Read tools cover the matter-centric core: search, matter snapshot, documents list,
   tasks, notes, deadline/health insight.
3. Writes are opt-in per scope (`tasks:write`, `notes:write`, `workflows:execute`), off by
   default, and every call — allowed or refused — lands in the org audit log.
4. Workflow execution is preview-first: dry-run is the default; execution requires the
   write scope *and* an explicit non-dry-run call.
5. Tool schemas are versioned and covered by a changelog from day one of beta.

**Non-goals for v1** (each one is a deliberate cut, not an oversight)

- Document *content* upload/download (privilege review implications; needs its own design)
- Billing, trust accounting, or payments writes (regulatory surface too sharp for beta)
- CJIS/gov environment support (FedRAMP posture makes this a fast-follow, not a v1 risk)
- A marketplace/directory listing model (distribution question, sequenced after GA)
- Fine-grained field-level permissions (org-level scopes first; field-level is post-GA)

## 4. Current state (public signal)

- REST API v2 at developer.filevine.io (Stoplight-hosted), US/CA/CJIS environments,
  webhook subscriptions, Certified Partner Integrations program.
- DataBridge ships analytics egress as near-real-time Snowflake shares — the precedent for
  "a governed, schema-stable contract instead of a DIY export."
- No public first-party MCP artifact as of 2026-07-13.

## 5. Design sketch (reference implementation attached)

The bundled server demonstrates the v1 shape end-to-end against mock data:

| Surface | Tools | Notes |
|---|---|---|
| Read core | `search_projects`, `get_project`, `list_documents` | Matter-centric; snapshot bundles docs+tasks+notes to cut round-trips |
| Insight | `matter_health_report`, `get_deadlines` | The differentiated layer: portfolio triage and rule-derived deadline chains, one call each |
| Writes (gated) | `create_task`, `add_note` | Validated inputs; refuse with a *teaching* error when scope absent |
| Workflows | `list_workflows`, `run_workflow` | Declarative library; dry-run default; idempotency guards |
| Data egress | `export_snapshot` | Schema-versioned extract with manifest — DataBridge in miniature; production points at real DataBridge |

Two production deltas from the reference implementation, decided deliberately:

1. **Auth:** beta uses org-scoped PATs minted in the existing admin console (fastest safe
   path); GA target is OAuth 2.1 authorization-code so end users authorize agents without
   handling raw keys. Client-credentials only for server-to-server partners.
2. **Audit:** reference server writes `audit.jsonl`; production emits the same event shape
   into Filevine's existing audit infrastructure so MCP actions appear in the org audit log
   alongside human actions — one audit story, not two.

## 6. Success metrics

| Metric | Beta target | Why this one |
|---|---|---|
| Time-to-first-successful-tool-call | < 10 min median | The whole DX in one number |
| Orgs with ≥1 weekly-active MCP connection | ≥ 8 of ~12 beta orgs | Adoption, not installation |
| Tool-call error rate (schema/auth errors) | < 5% after week 2 | Agent-UX quality |
| Write calls preceded by a dry-run or explicit human grant | 100% | The governance promise, measured |
| Support tickets per beta org per week | < 1 by week 4 | Docs + error messages doing their job |
| Beta-exit survey: "would be disappointed if removed" | ≥ 60% | Sean Ellis bar for GA case |

## 7. Rollout

1. **Private beta (6 weeks):** 8–12 design-partner firms (mix: PI high-volume, mid-size
   litigation, one gov-adjacent) + 2–3 Certified Partners. Weekly feedback synthesis →
   labeled issues (see `beta-program-plan.md`).
2. **Open beta announcement: LEX Summit 2026 (Oct 26–29, San Diego).** The stage where
   LOIS was unveiled is the right stage for "connect your own agent to your firm."
3. **GA:** gated on metrics above + security review + CJIS/gov decision.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Privilege/PII exposure through agent context windows | Read-only default; no document *content* in v1; scope model; customer-controlled connection points (mirror the no-training/no-retention posture Filevine already negotiates with LLM providers) |
| Hallucinated or over-eager writes | Dry-run default for workflows; validated write inputs; idempotency guards; 100%-audit metric |
| Unofficial servers fragment the DX story | Ship first-party; engage the three community maintainers directly (they're the most motivated beta testers in the ecosystem) |
| Tool-schema churn breaks agents silently | Versioned schemas + changelog from beta day one; deprecation policy before GA |
| Env sprawl (US/CA/CJIS) confuses provisioning | v1 = US + CA only; env pinned at credential-mint time, never inferred |

## 9. Open questions for the Senior PM

1. Does `run_workflow` route through the LOIS Workflows engine, or is MCP a separate
   execution path? (Product coherence says the former; beta speed may say the latter.)
2. Pricing/packaging: included in existing API tier, or a LOIS add-on?
3. Is there an internal MCP effort already scoped that this collides with or feeds?
4. What did the Certified Partner program learn about partner-side auth pain that should
   change the credential design here?
