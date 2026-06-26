# Demo Video Script

Target length: 4:30 to 5:00 minutes.

## 0:00 - Introduction

Hello, this is my SQL Server Incident Triage Agent for the Kaggle AI Agents Vibe
Coding Capstone Project. It is designed for DBAs and system engineers who need
to analyze SQL Server incidents quickly and safely.

## 0:20 - Problem

SQL Server incidents often arrive as long logs, failed SQL Agent job histories,
TempDB errors, database integrity warnings, deadlock errors, replication
messages, availability group alerts, or Query Store findings. During a
production incident, the DBA needs to classify the problem, understand severity,
collect evidence, and avoid unsafe actions.

## 0:50 - Why agents

This project uses agents because incident response has multiple roles. One agent
performs technical triage, one reviews safety and privacy risk, and one combines
the result into a clear DBA action plan. This separation helps avoid unsupported
claims and unsafe recommendations.

## 1:20 - Architecture

Show `assets/how_to_use_app.svg` first, then `assets/safety_first_agent_flow.svg`
or the architecture section in the README.

Explain the user workflow:

- A real DBA copies an incident from SSMS, SQL Agent history, SQL Server Error
  Log, monitoring, or application logs.
- The user pastes that real text into Incident input.
- Load sample incident is only for demo/testing, not for normal real usage.
- The user clicks Analyze Incident and reviews the result.

Then explain the agent architecture:

- Streamlit receives the incident.
- A privacy guard redacts sensitive values.
- A local rule engine always runs first.
- With explicit approval, Google ADK runs the multi-agent workflow.
- The triage agent uses a local FastMCP server with read-only tools.
- The app records human DBA approval but does not execute SQL.

## 2:00 - Demo 1: backup failure

Load `backup_failed_disk_full.txt`.

Explain that this sample simulates what a DBA would normally paste from SQL
Agent job history or an error log. Show that the agent detects Backup / Storage
with Critical severity. Point out the likely cause, verification steps, and
read-only SQL checks.

## 2:35 - Demo 2: TempDB or database integrity

Load `tempdb_space_pressure.txt` or `database_suspect_page_checksum.txt`.

Show that the agent recognizes a high-impact database incident and recommends
verification before operational action. Emphasize that the app suggests checks
but does not execute SQL.

## 3:10 - Demo 3: deadlock or availability group

Use either `deadlock_detected.txt` or `always_on_not_synchronizing.txt`.

For deadlock, show the category as Concurrency and the recommendation to inspect
the deadlock graph and lock order. For availability groups, show the High
Availability category, synchronization health, and failover caution.

## 3:45 - Security features

Show `assets/security_boundary_diagram.svg`, the privacy review panel, and the
external AI approval control. If no Gemini API key is configured, explain that
the external AI option remains disabled and the local triage engine still works.

Explain:

- external AI is opt-in
- redaction runs before ADK
- live SQL diagnostics are disabled by default
- the UI does not execute SQL
- SQL checks require DBA review

If time allows, briefly show `assets/incident_knowledge_loop.svg` and explain
that unknown incidents can become reusable redacted samples only after ADK
guidance and human approval.

## 4:20 - Build and course concepts

Mention the key concepts demonstrated:

- The project was developed and reviewed using VS Code and Google Antigravity
  IDE as coding/development tools.
- Google ADK multi-agent workflow
- MCP server
- Agent Skill runbook for SQL Server incident triage
- security guardrails
- focused code comments around ADK tool filtering, privacy, MCP read-only
  behavior, and SQL allowlisting
- 14 SQL Server incident scenarios
- optional user-approved custom sample creation for unknown incidents when ADK
  is configured
- agent tool use
- public GitHub setup instructions

If you show Antigravity in the video, briefly show the project opened there or
state the specific review/refinement task you used it for.

## 4:50 - Conclusion

This project demonstrates a practical business agent that reduces SQL Server
incident triage time, improves consistency, and keeps human DBA approval in the
loop for operational actions.
