# Platform MCP — Private Beta Program Plan

**Owner:** PM, API Platform · **Duration:** 6 weeks · **Written:** 2026-07-13 (work sample)

## Objective

Prove, with named firms and measured usage, that a first-party MCP server is safe enough
for legal matter data and useful enough that firms would object to losing it — and convert
that evidence into an open-beta announcement at LEX Summit 2026 (Oct 26–29, San Diego).

## Cohort (8–12 orgs + 2–3 partners)

| Slice | Count | Why |
|---|---|---|
| High-volume PI firms | 3–4 | Filevine's core; portfolio-triage value shows fastest at volume |
| Mid-size litigation | 2–3 | Deadline-chain and discovery workflows stress the insight tools |
| Gov-adjacent firm | 1 | Early read on CJIS-env demand before we commit to it |
| Certified Partners / consultancies | 2–3 | They feel auth + schema pain first and translate it precisely |
| Community MCP maintainers | invite 2 | They already built unofficial servers — the most motivated testers in the ecosystem, and this converts competitors into contributors |

**Entry criteria per org:** named champion, weekly office-hours commitment, signed beta
terms (non-GA disclaimer, data handling, feedback license), admin willing to do the
10-minute setup live on a call (that call IS the TTFTC test).

## Week-by-week arc

| Week | Focus | Milestone |
|---|---|---|
| 0 | Provisioning + onboarding calls | Every org connected; TTFTC measured live |
| 1–2 | Read + insight tools in daily use | ≥50% orgs with a weekly-active connection |
| 3 | Write scopes offered (opt-in) | ≥4 orgs enable a write scope; audit review with each |
| 4 | Workflows dry-run → execute | ≥3 orgs execute a workflow in production |
| 5 | Hardening + docs from observed failures | Error rate <5%; quickstart re-tested cold |
| 6 | Exit interviews + Sean Ellis survey | Go/no-go review for LEX announcement |

## Feedback instrumentation (signal, not anecdotes)

1. **Telemetry (continuous):** TTFTC funnel, weekly-active connections per org, calls and
   error classes per tool, dry-run→execute conversion, refused-write counts. Surfaced in
   the existing in-app API Usage tool + a weekly digest to the beta channel.
2. **Office hours (weekly, 25 min/org):** one structured question set — what did you try,
   where did it refuse/confuse, what did you wish it could do. Recorded, synthesized same day.
3. **Support tickets:** tagged `mcp-beta`, routed to the triage queue with telemetry links.
4. **Synthesis ritual (Fridays):** every input becomes either a labeled issue with
   acceptance criteria, a documented won't-fix with rationale sent back to the reporter,
   or an open question for the Senior PM with context attached. Nothing evaporates.

## Communication cadence

- **To beta firms:** Monday changelog note (what shipped, what's next, whose feedback
  drove it — named credit); 72h decision SLA on beta-blocking reports.
- **Internal:** weekly one-page status (adoption numbers, top 3 risks, decisions needed)
  to API Platform + Support + Security; enablement preview to Sales/Support in week 4 so
  release day surprises no one.

## Exit criteria (GA case)

- ≥8 orgs weekly-active in weeks 5–6; TTFTC median <10 min across all onboardings
- Error rate <5%; zero privilege/PII exclusion-list breaches (red-team pass clean)
- 100% of writes audited; ≥60% "very disappointed if removed" on exit survey
- Security sign-off + support runbook + docs cold-tested
- Pricing/packaging decision made (with Senior PM + GTM)

## Kill criteria (say them out loud now)

- Any confirmed exfiltration of excluded fields via tool composition → pause writes
  immediately, root-cause before resuming.
- <4 orgs weekly-active by week 4 → the value hypothesis is wrong; stop and re-scope
  rather than shipping a ghost town to GA.
