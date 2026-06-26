# Demo Video Script

Target length: 4:30 to 5:00 minutes.

## 0:00 - Introduction

Hello, this is my SQL Server Incident Triage Agent for the Kaggle AI Agents Vibe
Coding Capstone Project. It is designed for DBAs and system engineers who need
to analyze SQL Server incidents quickly and safely.

## 0:20 - Problem

SQL Server incidents often arrive as long logs, failed SQL Agent job histories,
deadlock errors, replication messages, or Query Store findings. During a
production incident, the DBA needs to classify the problem, understand severity,
collect evidence, and avoid unsafe actions.

## 0:50 - Why agents

This project uses agents because incident response has multiple roles. One agent
performs technical triage, one reviews safety and privacy risk, and one combines
the result into a clear DBA action plan. This separation helps avoid unsupported
claims and unsafe recommendations.

## 1:20 - Architecture

Show `docs/ARCHITECTURE.md` or the diagram in the README.

Explain the flow:

- Streamlit receives the incident.
- A privacy guard redacts sensitive values.
- A local rule engine always runs first.
- With explicit approval, Google ADK runs the multi-agent workflow.
- The triage agent uses a local FastMCP server with read-only tools.
- The app records human DBA approval but does not execute SQL.

## 2:00 - Demo 1: backup failure

Load `backup_failed_disk_full.txt`.

Show that the agent detects Backup / Storage with Critical severity. Point out
the likely cause, verification steps, and read-only SQL checks.

## 2:35 - Demo 2: active transaction

Load `active_transaction_log_full.txt`.

Show that the agent detects a transaction log issue caused by
`ACTIVE_TRANSACTION`. Emphasize that it recommends verification before any shrink
or operational action.

## 3:10 - Demo 3: replication or deadlock

Use either `replication_subscription_failed.txt` or `deadlock_detected.txt`.

For replication, show the agent identifying the failed subscription path. For
deadlock, show the category as Concurrency and the recommendation to inspect the
deadlock graph and transaction lock order.

## 3:45 - Security features

Show the privacy review panel and the external AI approval checkbox.

Explain:

- external AI is opt-in
- redaction runs before ADK
- live SQL diagnostics are disabled by default
- the UI does not execute SQL
- SQL checks require DBA review

## 4:20 - Build and course concepts

Mention the key concepts demonstrated:

- Google ADK multi-agent workflow
- MCP server
- security guardrails
- agent tool use
- public GitHub setup instructions

Only mention Google Antigravity if you actually opened the project there and can
show or describe that workflow honestly.

## 4:50 - Conclusion

This project demonstrates a practical business agent that reduces SQL Server
incident triage time, improves consistency, and keeps human DBA approval in the
loop for operational actions.

