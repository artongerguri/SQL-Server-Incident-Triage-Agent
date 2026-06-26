from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from src.memory import IncidentMemoryStore
from src.rules import build_local_analysis
from src.security import scan_and_redact
from src.sqlserver_tools import SqlServerReadOnlyClient, list_diagnostics


mcp = FastMCP(
    "sql-server-incident-triage",
    instructions=(
        "Read-only SQL Server incident triage tools. The server never accepts "
        "arbitrary SQL and live diagnostics are disabled by default."
    ),
)

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def analyze_incident(incident_text: str) -> dict[str, Any]:
    """Redact sensitive values and run deterministic SQL incident triage."""
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
    return {"diagnostics": list_diagnostics(include_queries=False)}


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def run_sql_diagnostic(diagnostic_name: str) -> dict[str, Any]:
    """Run one named diagnostic when live access is explicitly enabled."""
    return SqlServerReadOnlyClient().run(diagnostic_name)


@mcp.tool(annotations=READ_ONLY, structured_output=True)
def search_incident_memory(
    incident_text: str,
    category: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Find similar locally stored incidents using only redacted text."""
    privacy = scan_and_redact(incident_text)
    incidents = IncidentMemoryStore().find_similar(
        privacy.redacted_text,
        category=category,
        limit=limit,
    )
    return {"incidents": incidents}


if __name__ == "__main__":
    mcp.run(transport="stdio")
