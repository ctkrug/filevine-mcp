# Release Notes — Drafts (work sample)

Two artifacts: the customer-facing beta announcement, and the internal enablement note.
Written to be shippable without heavy editing — per the role's own bar.

---

## 1. Customer-facing — "What's New" entry

### Platform MCP (Private Beta): connect your AI assistant to your firm's matters

Your team already works alongside AI assistants. Starting today with a small group of
beta firms, those assistants can work alongside Filevine — safely.

**Platform MCP** is a new way to connect tools like Claude to your org using the open
Model Context Protocol. Ask "what needs attention across our matters this morning?" and
get portfolio-level answers drawn live from your Filevine data: stale matters, overdue
tasks, documents waiting on review, and deadline chains — including the ones nobody
calendared yet.

**Built for legal data from the first line:**

- **Read-only by default.** Your assistant can look things up the moment you connect.
  Creating tasks or notes requires write permissions an Account Admin explicitly grants —
  and can revoke at any time.
- **Preview before it acts.** Workflow runs default to a dry run: you see exactly which
  matters match and every task and note the workflow would create, before anything happens.
- **Everything on the record.** Every agent action — including the ones Filevine refused —
  appears in your org audit log with what, when, and under which credential.

**Beta scope:** matter search and snapshots, document lists (metadata only — never
document contents), portfolio health and deadline reports, and permission-gated tasks,
notes, and workflow runs. US and Canada environments.

Interested in the beta? Talk to your account manager, or watch for the open beta later
this year.

---

## 2. Internal enablement — Support & Sales one-pager

**What shipped:** Private beta of Platform MCP — a first-party MCP server letting
customer AI assistants (Claude Desktop/Code and other MCP clients) read Filevine data and,
with explicit admin-granted scopes, create tasks/notes and execute workflows.

**Who has it:** ~12 named beta orgs (list in the beta channel). Not visible to other
customers; no GA date committed publicly ("later this year" is the approved phrase).

**The 30-second pitch:** "Your AI assistant can now answer questions from your live
Filevine data and file the follow-up work — with admin-controlled permissions and a full
audit trail. It's the difference between an assistant that talks about your cases and one
that actually knows them."

**What it is NOT (say this proactively):**
- Not LOIS. LOIS Console is Filevine's own AI working inside the platform; Platform MCP
  is the governed door for assistants customers already use *outside* it. They complement.
- Not document access. Beta returns document *metadata* only, never contents.
- Not autonomous. Writes need admin-granted scopes; workflows preview by default.

**Likely questions →**
- *"Is our data training someone's model?"* Connection is customer-controlled; Filevine's
  existing no-training/no-retention posture with AI providers applies. Escalate specifics
  to Security via the beta channel.
- *"Can we get in?"* Beta is capped for feedback quality. Log interest with the `mcp-beta`
  tag — the waitlist directly shapes GA timing.
- *"What does it cost?"* Beta is free to participants; packaging TBD ("we'll announce with
  open beta").
- *"Something broke."* Tag ticket `mcp-beta`; triage SLA <24h, answer-to-firm <72h.

**Known rough edges (beta-honest):** client secrets expire yearly and are non-renewable
(early-warning banners ship in-beta); multi-org PATs need explicit org selection; rate
limits for agent traffic are still being tuned with real usage.
