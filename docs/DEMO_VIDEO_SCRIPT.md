# Demo Video Script

Target length: 4:30 to 5:00 minutes.

Use this as a read-aloud script. Keep the pace calm and do not spend too long on
any single screen. Avoid showing `.env`, API keys, passwords, or connection
strings.

## 0:00 - 0:15 | Personal Introduction

Show on screen: project README title or cover image.

Say:

Hello, my name is Arton Gerguri. This is my submission for the Kaggle AI Agents:
Intensive Vibe Coding Capstone Project. The project is called SQL Server
Incident Triage Agent, and it is designed for DBAs and system engineers.

## 0:15 - 0:45 | Problem Statement

Show on screen: README overview or `assets/how_to_use_app.svg`.

Say:

SQL Server incidents often arrive as long and noisy logs. They can come from
SSMS, SQL Agent Job History, SQL Server Error Log, monitoring tools, or
application logs. During a production issue, a DBA has to quickly understand the
category, severity, likely cause, and safe verification steps.

This is important because a wrong action, such as shrinking files, killing
sessions, forcing failover, or changing replication too early, can make the
incident worse. The goal of this agent is to support the first triage phase in a
safe and consistent way.

## 0:45 - 1:10 | How the User Uses the App

Show on screen: `assets/how_to_use_app.svg`.

Say:

The normal user workflow is simple. A DBA copies the real incident message from
SSMS, SQL Agent history, SQL Server logs, monitoring, or application logs. Then
the user pastes that text into the Incident input field and clicks Analyze
Incident.

The Load sample incident option is only for demos and testing. In real use, the
user pastes the actual incident text. The application then returns a structured
triage result, but it does not execute SQL automatically.

## 1:10 - 1:45 | Why Agents

Show on screen: `assets/safety_first_agent_flow.svg`.

Say:

I used agents because incident response has multiple responsibilities. In this
project, the ADK workflow separates those responsibilities into three roles.

The SQL triage specialist analyzes the incident and uses read-only MCP tools.
The safety reviewer checks the advice for privacy risk, unsafe actions, and
unsupported claims. The incident coordinator combines the diagnosis and safety
review into one DBA-facing action plan.

This makes the agent more useful than a single prompt because it separates
technical triage from safety review.

## 1:45 - 2:20 | Architecture

Show on screen: README architecture section or `assets/safety_first_agent_flow.svg`.

Say:

The architecture is local-first and safety-first. Streamlit receives the
incident text. A privacy guard redacts sensitive-looking values such as users,
hosts, database names, IP addresses, paths, and secrets. Then the local rule
engine always runs first, so the application works even without an API key.

If the user explicitly approves external AI sharing and a Google API key is
configured, Google ADK can run the multi-agent workflow. The triage agent uses a
local FastMCP server with read-only tools. The UI displays suggested SQL checks
for DBA review, but the application itself does not execute SQL.

## 2:20 - 3:00 | Demo 1: Backup Failure

Show on screen: Streamlit app.

Actions:

1. Load `backup_failed_disk_full.txt`.
2. Click **Analyze Incident**.
3. Show severity, category, likely cause, verification steps, and SQL checks.

Say:

For the first demo, I am using a sample incident that simulates a failed SQL
Agent backup job. In real usage, this text would usually be copied from SQL
Agent history or the SQL Server error log.

The agent classifies this as Backup / Storage with Critical severity. It
identifies insufficient disk space as the likely cause and suggests safe
verification steps, such as checking backup destination space, SQL Agent job
history, and related error log messages.

The SQL checks shown here are read-only suggestions for a DBA to review. The app
does not run them.

## 3:00 - 3:30 | Demo 2: TempDB or Integrity Incident

Show on screen: Streamlit app.

Actions:

1. Load `tempdb_space_pressure.txt` or `database_suspect_page_checksum.txt`.
2. Click **Analyze Incident**.
3. Show the category, severity, and recommended actions.

Say:

For the second demo, I am showing another high-impact SQL Server incident. The
agent recognizes the incident category and recommends verification before
operational action.

This is important because database incidents often require caution. The tool
helps organize the first response, but final actions still require human DBA
judgment and approval.

## 3:30 - 4:05 | Security Features

Show on screen: `assets/security_boundary_diagram.svg`, then the app privacy
review panel.

Say:

Security is a core part of the design. External AI is opt-in. Redaction runs
before optional ADK analysis. The original incident text stays local unless the
user explicitly approves sharing redacted text.

Live SQL diagnostics are disabled by default. The MCP server exposes named
read-only tools and does not accept arbitrary SQL. The UI also does not execute
SQL. It only displays checks for DBA review.

## 4:05 - 4:30 | Build and Course Concepts

Show on screen: VS Code, Google Antigravity IDE, or README project structure.

Say:

I built and tested the project using Python, Streamlit, Google ADK, FastMCP,
SQLite, and pytest. I used VS Code as the primary development environment and
Google Antigravity IDE as an agentic review and refinement tool.

The project demonstrates multiple course concepts: an ADK multi-agent workflow,
an MCP server, security guardrails, Agent Skill runbooks, agent tool use,
deployable GitHub documentation, focused code comments, tests, and visual
architecture diagrams.

## 4:30 - 4:50 | Optional Learning Loop

Show on screen: `assets/incident_knowledge_loop.svg`.

Say:

The project also includes a controlled learning loop for unknown incidents. If
no local rule matches, and ADK guidance is available, the user can save a
redacted proposed rule only after human review and approval.

This does not automatically activate the rule or modify the source code. It
creates a local JSON proposal that can later be reviewed, converted into a
deterministic `TriageRule`, and covered with tests.

In the UI, this appears as a Propose a new rule panel. The user must confirm the
name, category, severity, candidate keywords, notes, and approval checkbox before
the proposal is saved.

## 4:50 - 5:00 | Conclusion

Show on screen: GitHub repository or final app result.

Say:

In summary, this project is a practical business agent that helps reduce SQL
Server incident triage time, improves consistency, and keeps human DBA approval
in the loop for operational actions.
