# filevine-mcp — recorded demo session
Recorded 2026-07-14 13:52Z against mock data (six fictional plaintiff-side matters). Every tool result below is the server's real output, captured over stdio by a scripted MCP client (`demo_agent.py`).

---

## Step 1 — Morning triage · `insight`
User asks: “What needs attention across our matters this morning?” One tool call returns portfolio-level triage instead of six matter-by-matter reads.
**Tool:** `matter_health_report`  
**Args:** `{}`

```json
{
  "generated": "2026-07-14",
  "staleMatters": [
    {
      "project": "Hale v. Denver Transit Authority",
      "projectId": 10246,
      "daysSinceActivity": 74,
      "phase": "Treatment",
      "leadAttorney": "D. Okafor"
    },
    {
      "project": "Whitfield v. Carter Trucking Co.",
      "projectId": 10243,
      "daysSinceActivity": 46,
      "phase": "Litigation",
      "leadAttorney": "D. Okafor"
    }
  ],
  "overdueTasks": [
    {
      "project": "Whitfield v. Carter Trucking Co.",
      "task": "Review defendant RFP responses Set 1",
      "assignee": "S. Brandt",
      "dueDate": "2026-06-11",
      "daysOverdue": 33,
      "priority": "high"
    },
    {
      "project": "Whitfield v. Carter Trucking Co.",
      "task": "Schedule client deposition prep",
      "assignee": "D. Okafor",
      "dueDate": "2026-06-21",
      "daysOverdue": 23,
      "priority": "medium"
    },
    {
      "project": "Estate of Romero v. Lakeside Medical",
      "task": "Conflict check and engagement letter",
      "assignee": "intake.desk",
      "dueDate": "2026-07-03",
      "daysOverdue": 11,
      "priority": "high"
    },
    {
      "project": "Estate of Romero v. Lakeside Medical",
      "task": "Assign lead attorney",
      "assignee": "S. Brandt",
      "dueDate": "2026-07-06",
      "daysOverdue": 8,
      "priority": "high"
    }
  ],
  "documentsStuckInReview": [
    {
      "project": "Whitfield v. Carter Trucking Co.",
      "filename": "Whitfield_DefResponses_RFP_Set1.pdf",
      "daysInReview": 47
    },
    {
      "project": "Estate of Romero v. Lakeside Medical",
      "filename": "Romero_IntakeQuestionnaire.pdf",
      "daysInReview": 18
    }
  ],
  "solWithin180Days": [
    {
      "project": "Hale v. Denver Transit Authority",
      "solDate": "2026-10-03",
      "daysRemaining": 81
    },
    {
      "project": "Okafor v. BrightPath Insurance",
      "solDate": "2026-12-10",
      "daysRemaining": 149
    }
  ],
  "unassignedMatters": [
    "Estate of Romero v. Lakeside Medical"
  ]
}
```

---

## Step 2 — Morning triage · `insight`
Follow-up: “What deadlines am I actually up against?” The deadline-chain engine derives dates the health report can't see — including a discovery meet-and-confer window that has ALREADY passed on Whitfield, and Hale's governmental notice date.
**Tool:** `get_deadlines`  
**Args:** `{}`

```json
{
  "generated": "2026-07-14",
  "disclaimer": "Illustrative, Colorado-flavored ruleset to demonstrate deadline chains \u2014 not legal advice. A production implementation would source per-jurisdiction rules and let firms configure their own.",
  "deadlines": [
    {
      "projectId": 10243,
      "project": "Whitfield v. Carter Trucking Co.",
      "rule": "Discovery meet-and-confer window",
      "basis": "35 days from service of responses (Whitfield_DefResponses_RFP_Set1.pdf)",
      "date": "2026-07-02",
      "daysRemaining": -12,
      "severity": "overdue"
    },
    {
      "projectId": 10245,
      "project": "Okafor v. BrightPath Insurance",
      "rule": "Settlement disbursement clock",
      "basis": "21-day funding/disbursement window from agreement draft (Okafor_SettlementAgreement_DRAFT.docx)",
      "date": "2026-08-02",
      "daysRemaining": 19,
      "severity": "critical"
    },
    {
      "projectId": 10241,
      "project": "Alvarez v. Summit Logistics",
      "rule": "Demand response follow-up",
      "basis": "30-day insurer response window from latest demand doc (Alvarez_DemandLetter_DRAFT_v3.docx)",
      "date": "2026-08-08",
      "daysRemaining": 25,
      "severity": "critical"
    },
    {
      "projectId": 10246,
      "project": "Hale v. Denver Transit Authority",
      "rule": "Governmental notice of claim",
      "basis": "CGIA-style 182-day notice from incident date",
      "date": "2026-10-02",
      "daysRemaining": 80,
      "severity": "high"
    },
    {
      "projectId": 10246,
      "project": "Hale v. Denver Transit Authority",
      "rule": "Statute of limitations",
      "basis": "Matter SOL date on file",
      "date": "2026-10-03",
      "daysRemaining": 81,
      "severity": "high"
    },
    {
      "projectId": 10245,
      "project": "Okafor v. BrightPath Insurance",
      "rule": "Statute of limitations",
      "basis": "Matter SOL date on file",
      "date": "2026-12-10",
      "daysRemaining": 149,
      "severity": "medium"
    },
    {
      "projectId": 10243,
      "project": "Whitfield v. Carter Trucking Co.",
      "rule": "Statute of limitations",
      "basis": "Matter SOL date on file",
      "date": "2027-06-23",
      "daysRemaining": 344,
      "severity": "low"
    },
    {
      "projectId": 10241,
      "project": "Alvarez v. Summit Logistics",
      "rule": "Statute of limitations",
      "basis": "Matter SOL date on file",
      "date": "2027-11-04",
      "daysRemaining": 478,
      "severity": "low"
    },
    {
      "projectId": 10242,
      "project": "Nguyen v. Ridgeline P
  ... (truncated; full output in transcript.json)
```

---

## Step 3 — Workflow preview · `dry-run`
“Run the SOL watchdog.” The engine defaults to a dry run: here is exactly what it WOULD do — which matters matched the 180-day window and every task/note it would create — before anything is touched.
**Tool:** `run_workflow`  
**Args:** `{"workflow_id": "sol-watchdog"}`

```json
{
  "workflow": "SOL & Notice Watchdog",
  "dryRun": true,
  "matchedMatters": [
    "Okafor v. BrightPath Insurance",
    "Hale v. Denver Transit Authority"
  ],
  "plannedActions": [
    {
      "type": "create_task",
      "projectId": 10245,
      "project": "Okafor v. BrightPath Insurance",
      "title": "SOL/notice filing-readiness check: Okafor v. BrightPath Insurance (deadline 2026-12-10)",
      "assignee": "S. Brandt",
      "dueDate": "2026-07-21",
      "priority": "critical"
    },
    {
      "type": "add_note",
      "projectId": 10245,
      "project": "Okafor v. BrightPath Insurance",
      "text": "[sol-watchdog] SOL/notice date 2026-12-10 is 149 days out. Filing-readiness task created for S. Brandt."
    },
    {
      "type": "create_task",
      "projectId": 10246,
      "project": "Hale v. Denver Transit Authority",
      "title": "SOL/notice filing-readiness check: Hale v. Denver Transit Authority (deadline 2026-10-03)",
      "assignee": "D. Okafor",
      "dueDate": "2026-07-21",
      "priority": "critical"
    },
    {
      "type": "add_note",
      "projectId": 10246,
      "project": "Hale v. Denver Transit Authority",
      "text": "[sol-watchdog] SOL/notice date 2026-10-03 is 81 days out. Filing-readiness task created for D. Okafor."
    }
  ],
  "skipped": []
}
```

---

## Step 4 — Workflow preview · `guardrail`
“Looks right — execute the stale-matter sweep for real.” REFUSED: the server is in read-only mode. An agent does not get write access to legal matter data by default; a human has to grant it out-of-band.
**Tool:** `run_workflow`  
**Args:** `{"workflow_id": "stale-matter-sweep", "dry_run": false}`

```json
{
  "error": "Write tools are disabled (read-only mode). The operator must set FILEVINE_MCP_ALLOW_WRITES=1 to enable task/note creation. This is deliberate: agents should not modify legal matter data without an explicit human decision.",
  "hint": "Re-run with dry_run=true to preview."
}
```

---

## Step 5 — Human decision · `guardrail`
The operator — a human — restarts the server with FILEVINE_MCP_ALLOW_WRITES=1. Granting an agent write access to matters is an explicit, logged, out-of-band decision, not something the agent can talk its way into.

---

## Step 6 — Act · `action`
Same command, writes enabled: the sweep files reactivation tasks on every matter that has sat quiet past 21 days and stamps each with an explanatory note.
**Tool:** `run_workflow`  
**Args:** `{"workflow_id": "stale-matter-sweep", "dry_run": false}`

```json
{
  "workflow": "Stale Matter Sweep",
  "dryRun": false,
  "matchedMatters": [
    "Whitfield v. Carter Trucking Co.",
    "Hale v. Denver Transit Authority"
  ],
  "executedActions": [
    {
      "taskId": 9101,
      "projectId": 10243,
      "title": "Reactivate: Whitfield v. Carter Trucking Co. \u2014 46 days without activity",
      "assignee": "D. Okafor",
      "dueDate": "2026-07-17",
      "status": "open",
      "priority": "high"
    },
    {
      "noteId": 7101,
      "projectId": 10243,
      "authorId": "mcp-agent",
      "date": "2026-07-14",
      "text": "[stale-matter-sweep] No matter activity in 46 days (last touch 2026-05-29). Reactivation task filed to D. Okafor."
    },
    {
      "taskId": 9102,
      "projectId": 10246,
      "title": "Reactivate: Hale v. Denver Transit Authority \u2014 74 days without activity",
      "assignee": "D. Okafor",
      "dueDate": "2026-07-17",
      "status": "open",
      "priority": "high"
    },
    {
      "noteId": 7102,
      "projectId": 10246,
      "authorId": "mcp-agent",
      "date": "2026-07-14",
      "text": "[stale-matter-sweep] No matter activity in 74 days (last touch 2026-05-01). Reactivation task filed to D. Okafor."
    }
  ],
  "skipped": []
}
```

---

## Step 7 — Act · `action`
Acting on the deadline finding: a well-scoped, critical task on Whitfield — the 156-page RFP response has been unreviewed for 47 days and the meet-and-confer window already closed.
**Tool:** `create_task`  
**Args:** `{"project_id": 10243, "title": "Escalate: partner review of RFP Set 1 objections \u2014 meet-and-confer window passed", "assignee": "D. Okafor", "due_date": "2026-07-16", "priority": "critical"}`

```json
{
  "created": {
    "taskId": 9103,
    "projectId": 10243,
    "title": "Escalate: partner review of RFP Set 1 objections \u2014 meet-and-confer window passed",
    "assignee": "D. Okafor",
    "dueDate": "2026-07-16",
    "status": "open",
    "priority": "critical"
  }
}
```

---

## Step 8 — Act · `action`
The matter file gets the context, not just the task — the next person who opens Whitfield sees why the escalation exists.
**Tool:** `add_note`  
**Args:** `{"project_id": 10243, "text": "[triage] Meet-and-confer window on Defendant's RFP Set 1 responses (served 2026-05-28) closed 2026-07-02. Escalation task filed to D. Okafor 2026-07-14; recommend serving deficiency letter with the meet-and-confer request to preserve the objection record."}`

```json
{
  "created": {
    "noteId": 7103,
    "projectId": 10243,
    "authorId": "mcp-agent",
    "date": "2026-07-14",
    "text": "[triage] Meet-and-confer window on Defendant's RFP Set 1 responses (served 2026-05-28) closed 2026-07-02. Escalation task filed to D. Okafor 2026-07-14; recommend serving deficiency letter with the meet-and-confer request to preserve the objection record."
  }
}
```

---

## Step 9 — Extract · `action`
Finally: “Snapshot the org for the BI pipeline.” Four CSVs plus a manifest with row counts and a frozen column contract — a point-in-time extract in the spirit of DataBridge.
**Tool:** `export_snapshot`  
**Args:** `{}`

```json
{
  "generated": "2026-07-14T13:52:51.627061+00:00",
  "mode": "mock",
  "schemaVersion": "1.0",
  "path": "/Users/Krug/Desktop/Claude/pocs/filevine-mcp/exports/snapshot-20260714T135251Z",
  "tables": [
    {
      "table": "projects",
      "file": "projects.csv",
      "rows": 6,
      "columns": [
        "projectId",
        "projectName",
        "clientName",
        "practiceArea",
        "phase",
        "incidentDate",
        "openedDate",
        "lastActivity",
        "leadAttorney",
        "sol_date",
        "court",
        "caseNumber",
        "opposingCounsel",
        "estValue"
      ]
    },
    {
      "table": "tasks",
      "file": "tasks.csv",
      "rows": 13,
      "columns": [
        "taskId",
        "projectId",
        "title",
        "assignee",
        "dueDate",
        "status",
        "priority"
      ]
    },
    {
      "table": "documents",
      "file": "documents.csv",
      "rows": 10,
      "columns": [
        "documentId",
        "projectId",
        "filename",
        "docType",
        "uploadedDate",
        "reviewStatus",
        "pages"
      ]
    },
    {
      "table": "notes",
      "file": "notes.csv",
      "rows": 8,
      "columns": [
        "noteId",
        "projectId",
        "authorId",
        "date",
        "text"
      ]
    }
  ]
}
```

---

## Step 10 — Prove it · `audit`
Every one of the 8 calls this session — including the refused one — is in audit.jsonl with tool, arguments, mode, and timestamp. When a firm asks “what did the agent do to our matters?”, the answer is a file, not a shrug.

```json
{
  "auditEntries": 8,
  "lastThree": [
    {
      "ts": "2026-07-14T13:52:51.621924+00:00",
      "tool": "create_task",
      "args": {
        "project_id": 10243,
        "title": "Escalate: partner review of RFP Set 1 objections \u2014 meet-and-confer window passed",
        "assignee": "D. Okafor",
        "due_date": "2026-07-16",
        "priority": "critical"
      },
      "mode": "mock",
      "writes_enabled": true
    },
    {
      "ts": "2026-07-14T13:52:51.624389+00:00",
      "tool": "add_note",
      "args": {
        "project_id": 10243,
        "text": "[triage] Meet-and-confer window on Defendant's RFP Set 1 responses (served 2026-05-28) closed 2026-07-02. Escalation task filed to D. Okafor 2026-07-14; recommend serving deficiency letter with the me"
      },
      "mode": "mock",
      "writes_enabled": true
    },
    {
      "ts": "2026-07-14T13:52:51.626771+00:00",
      "tool": "export_snapshot",
      "args": {},
      "mode": "mock",
      "writes_enabled": true
    }
  ]
}
```
