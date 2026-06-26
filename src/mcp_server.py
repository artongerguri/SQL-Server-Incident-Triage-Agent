"""FastMCP server exposing read-only SQL Server triage tools.

The MCP server is the tool boundary between agents and deterministic project
capabilities. It offers named, typed functions instead of arbitrary database or
shell access.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from src.memory import IncidentMemoryStore
from src.rules import build_local_analysis
from src.security import scan_and_redact
from src.sqlserver_tools import SqlServerReadOnlyClient, list_diagnostics


# The server-level instructions are visible to MCP clients and describe the
# contract that every exposed tool must follow.
mcp = FastMCP(
    "sql-server-incident-triage",
    instructions=(
        "Read-only SQL Server incident triage tools. The server never accepts "
        "arbitrary SQL and live diagnostics are disabled by default."
    ),
)

# Tool annotations advertise the safety properties to MCP-aware clients. They do
# not replace server-side checks, but they make intent explicit for agents.
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def analyze_incident(incident_text: str) -> dict[str, Any]:
    """Redact sensitive values and run deterministic SQL incident triage."""
    # The MCP tool performs redaction itself so external MCP clients cannot
    # accidentally bypass the same privacy path used by the UI.
    privacy = scan_and_redact(incident_text)
    return {
        "analysis": build_local_analysis(privacy.redacted_text),
        "privacy_findings": [
            {"kind": finding.kind, "count": finding.count}
            for finding in privacy.findings
        ],
        "input_truncated": privacy.truncated,
    }


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def list_sql_diagnostics() -> dict[str, Any]:
    """List the allowlisted SQL Server diagnostic operations and permissions."""
    # ADK receives names/descriptions by default, not full SQL text.
    return {"diagnostics": list_diagnostics(include_queries=False)}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def run_sql_diagnostic(diagnostic_name: str) -> dict[str, Any]:
    """Run one named diagnostic when live access is explicitly enabled."""
    # The MCP boundary accepts only diagnostic names. Arbitrary SQL text never
    # crosses this interface, which keeps the tool read-only and auditable.
    return SqlServerReadOnlyClient().run(diagnostic_name)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def search_incident_memory(
    incident_text: str,
    category: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Find similar locally stored incidents using only redacted text."""
    # Search uses redacted text and category filtering, which keeps memory local
    # and prevents original incident details from being needed.
    privacy = scan_and_redact(incident_text)
    incidents = IncidentMemoryStore().find_similar(
        privacy.redacted_text,
        category=category,
        limit=limit,
    )
    return {"incidents": incidents}


if __name__ == "__main__":
    # ADK starts this process over stdio, which is the simplest local transport
    # for a demo-safe MCP server.
    mcp.run(transport="stdio")
