# Kaggle Writeup Draft

## Project title

SQL Server Incident Triage Agent

## Subtitle

An ADK multi-agent assistant that turns SQL Server incident logs into a safe DBA triage plan.

## Track

Agents for Business

## Problem

SQL Server incidents often arrive as long error logs, failed SQL Agent job
messages, replication errors, TempDB pressure, availability group warnings,
deadlock messages, corruption signals, login failures, or Query Store findings.
During a production incident, a DBA or system engineer has to quickly identify
the likely category, severity, evidence to collect, and the next safe action.
This is time-sensitive work: a wrong action can make recovery slower or increase
business downtime.

## Solution

This project provides a SQL Server Incident Triage Agent. The user pastes an
incident message into a Streamlit app or loads a sample incident. The app returns
a structured triage report with:

- incident category
- severity
- likely cause
- verification steps
- recommended DBA actions
- read-only SQL checks
- privacy review
- optional ADK multi-agent analysis

The local deterministic rule engine always runs first, so the project remains
usable even when external AI access is not configured. If the user explicitly
approves external AI sharing and `GOOGLE_API_KEY` is configured, a Google ADK
workflow adds a multi-agent review layer.

## Why agents

Incident triage benefits from multiple roles. In this project, the ADK workflow
uses three agents:

- `sql_triage_specialist`: classifies the issue and uses read-only MCP tools
  for deterministic context.
- `safety_reviewer`: checks the advice for unsupported claims, privacy exposure,
  and unsafe operational actions.
- `incident_coordinator`: combines the diagnosis and safety review into a final
  DBA-facing action plan.

This separation makes the agent more useful than a single prompt because the
workflow explicitly separates technical diagnosis from safety review.

## Architecture

The app follows a safety-first flow:

1. User enters an incident in Streamlit.
2. A privacy guard redacts secrets, emails, IPs, users, hosts, database names,
   and paths.
3. The local rule engine creates a deterministic triage result.
4. The Agent Skill runbook documents the reusable SQL Server triage procedure.
5. Optional SQLite memory stores only redacted previews and classifications.
6. With explicit user approval, ADK runs triage, safety review, and coordination
   agents.
7. The triage agent uses a FastMCP server with read-only tools.
8. The UI records human DBA approval for suggested SQL checks but does not
   execute SQL.

See `docs/ARCHITECTURE.md` and the static diagram assets:

- `assets/how_to_use_app.svg`
- `assets/safety_first_agent_flow.svg`
- `assets/security_boundary_diagram.svg`
- `assets/incident_knowledge_loop.svg`

## Course concepts demonstrated

| Key concept | Demonstration |
| --- | --- |
| Agent / multi-agent system with ADK | `src/adk_workflow.py` implements triage, safety, and coordinator agents. |
| MCP Server | `src/mcp_server.py` exposes read-only incident analysis, diagnostics listing, and memory search tools. |
| Security features | `src/security.py` redacts sensitive values, enforces SQL allowlists, and gates external AI sharing behind explicit approval. |
| Agent Skills | `skills/sql-server-incident-triage/SKILL.md` captures the reusable SQL Server triage runbook and category reference. |
| Agent tool use | The ADK triage agent calls MCP tools instead of relying only on free-form model reasoning. |
| Deployability | The public repository includes setup instructions, environment configuration, and tests. |

## Safety and privacy

The project avoids common risks for database assistants:

- No production credentials are stored in source code.
- The app does not execute SQL from the UI.
- External AI access is disabled unless the user opts in.
- Only redacted, length-limited incident text is sent to the ADK workflow.
- The MCP server never accepts arbitrary SQL.
- Live SQL diagnostics are disabled by default and use named static queries only.
- The UI records human DBA approval separately from analysis.

For unknown incidents, the app can create a local rule proposal after ADK
guidance and human approval. This is deliberately not automatic rule creation:
the proposal is saved as JSON under `data/rule_proposals/` and must be manually
reviewed, converted into a deterministic `TriageRule`, and covered by tests
before it becomes active.

## Demo scenario

The repository includes 14 anonymized sample incidents covering backup/storage,
transaction log pressure, replication, Query Store performance, deadlocks,
TempDB pressure, blocking, database integrity, login failures, Always On health,
backup chain risk, transaction log autogrowth, memory pressure, and connectivity
timeouts.

For a 5-minute video, the demo can show a focused subset:

1. failed backup because the target disk is full
2. TempDB space pressure
3. database suspect / page checksum warning
4. SQL Server deadlock victim error 1205
5. Always On database not synchronizing

For each sample, the app shows the category, severity, likely cause, verification
steps, recommended actions, privacy review, and safe SQL checks.

## Business value

The agent helps reduce initial triage time, standardize incident response, and
avoid risky actions during production support. This is valuable for business
systems where SQL Server downtime affects internal operations, customer-facing
services, reporting, or transaction processing.

## Implementation quality

The project includes focused tests for rule matching, privacy redaction, memory,
MCP/ADK integration, and SQL allowlist behavior. The local engine works without
network access, while the ADK workflow adds optional AI reasoning when configured.
The Agent Skill runbook keeps domain triage procedure separate from code, making
the project easier to review, reuse, and extend.

The project was developed using Visual Studio Code as the primary IDE and Google
Antigravity IDE as an agentic development/review environment. This workflow
matches the course theme of vibe coding while keeping the final implementation
reviewable through code, tests, diagrams, and documentation.

The implementation also includes broad targeted comments and docstrings across
the app, source modules, and tests. The most important comments document
safety-critical code paths: ADK tool filtering, MCP read-only behavior, privacy
redaction, local memory, SQL allowlisting, and user-approved rule proposal
storage. The comments explain design and behavior decisions rather than
repeating simple syntax.

## Limitations and future work

- Add richer evidence ingestion from SQL Server error logs, Windows event logs,
  and monitoring systems.
- Convert high-value rule proposals into reviewed deterministic rules.
- Add optional Markdown/PDF export after the triage result is finalized.
- Test live SQL diagnostics against a dedicated non-production SQL Server login.
- Add deployment instructions for Streamlit Community Cloud or Cloud Run if a
  live demo is preferred over a public GitHub repository.
