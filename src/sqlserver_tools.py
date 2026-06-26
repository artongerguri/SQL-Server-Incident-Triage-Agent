"""Optional live SQL Server diagnostic tools.

Live database access is disabled by default. When enabled for a controlled demo
or non-production environment, callers can run only named static diagnostics
through a read-only ODBC connection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any

from src.security import assert_read_only_sql


@dataclass(frozen=True)
class SqlDiagnostic:
    """Definition for one allowlisted SQL Server diagnostic query."""

    name: str
    description: str
    query: str
    required_permission: str

    def to_dict(self, include_query: bool = True) -> dict:
        """Serialize the diagnostic, optionally hiding the raw SQL text."""
        value = asdict(self)
        if not include_query:
            value.pop("query")
        return value


# Static diagnostics are safer than model-generated SQL because each query can be
# reviewed, tested, permission-scoped, and validated against the allowlist.
DIAGNOSTICS: dict[str, SqlDiagnostic] = {
    "database_health": SqlDiagnostic(
        name="database_health",
        description="Database state, recovery model, and log reuse wait.",
        query="""
            SELECT TOP (100) name, state_desc, recovery_model_desc,
                log_reuse_wait_desc
            FROM sys.databases
            ORDER BY name;
        """,
        required_permission="VIEW ANY DATABASE",
    ),
    "disk_volumes": SqlDiagnostic(
        name="disk_volumes",
        description="Volume capacity and free space for SQL Server database files.",
        query="""
            SELECT DISTINCT TOP (100) vs.volume_mount_point,
                vs.total_bytes, vs.available_bytes
            FROM sys.master_files AS mf
            CROSS APPLY sys.dm_os_volume_stats(mf.database_id, mf.file_id) AS vs
            ORDER BY vs.volume_mount_point;
        """,
        required_permission="VIEW SERVER STATE",
    ),
    "active_requests": SqlDiagnostic(
        name="active_requests",
        description="Active requests, waits, blockers, and statement text.",
        query="""
            SELECT TOP (50) r.session_id, r.status, r.command, r.wait_type,
                r.blocking_session_id, r.cpu_time, r.total_elapsed_time,
                LEFT(t.text, 4000) AS statement_text
            FROM sys.dm_exec_requests AS r
            CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) AS t
            WHERE r.session_id <> @@SPID
            ORDER BY r.total_elapsed_time DESC;
        """,
        required_permission="VIEW SERVER STATE",
    ),
    "agent_failures": SqlDiagnostic(
        name="agent_failures",
        description="Recent failed SQL Agent job outcomes.",
        query="""
            SELECT TOP (50) j.name, h.run_date, h.run_time, h.run_duration,
                h.message
            FROM msdb.dbo.sysjobhistory AS h
            INNER JOIN msdb.dbo.sysjobs AS j ON j.job_id = h.job_id
            WHERE h.step_id = 0 AND h.run_status = 0
            ORDER BY h.instance_id DESC;
        """,
        required_permission="SQLAgentReaderRole in msdb",
    ),
    "query_store_top_cpu": SqlDiagnostic(
        name="query_store_top_cpu",
        description="Top Query Store statements by average CPU in the current database.",
        query="""
            SELECT TOP (20) q.query_id, p.plan_id,
                SUM(rs.count_executions) AS executions,
                AVG(rs.avg_cpu_time) AS avg_cpu_time,
                LEFT(qt.query_sql_text, 4000) AS query_text
            FROM sys.query_store_query_text AS qt
            INNER JOIN sys.query_store_query AS q
                ON q.query_text_id = qt.query_text_id
            INNER JOIN sys.query_store_plan AS p ON p.query_id = q.query_id
            INNER JOIN sys.query_store_runtime_stats AS rs ON rs.plan_id = p.plan_id
            GROUP BY q.query_id, p.plan_id, qt.query_sql_text
            ORDER BY avg_cpu_time DESC;
        """,
        required_permission="VIEW DATABASE STATE",
    ),
    "replication_jobs": SqlDiagnostic(
        name="replication_jobs",
        description="Replication-related SQL Agent jobs and enabled state.",
        query="""
            SELECT TOP (100) j.name, j.enabled, c.name AS category_name,
                j.date_modified
            FROM msdb.dbo.sysjobs AS j
            INNER JOIN msdb.dbo.syscategories AS c ON c.category_id = j.category_id
            WHERE c.name LIKE '%Replication%'
            ORDER BY j.date_modified DESC;
        """,
        required_permission="SQLAgentReaderRole in msdb",
    ),
}


def list_diagnostics(include_queries: bool = False) -> list[dict]:
    # ADK sees diagnostic names and descriptions by default; full SQL text is
    # shown in the UI for human review, not used as model-executable input.
    return [
        diagnostic.to_dict(include_query=include_queries)
        for diagnostic in DIAGNOSTICS.values()
    ]


class SqlServerReadOnlyClient:
    """Executes only named, static diagnostics with a read-only ODBC connection."""

    def __init__(
        self,
        connection_string: str | None = None,
        enabled: bool | None = None,
        query_timeout_seconds: int | None = None,
        max_rows: int = 100,
    ):
        # Constructor parameters make the client testable; environment variables
        # make it easy to configure for local demos without code changes.
        self.connection_string = connection_string or os.getenv(
            "SQLSERVER_CONNECTION_STRING", ""
        )
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("SQLSERVER_MCP_ENABLE_LIVE", "false").lower() == "true"
        )
        self.query_timeout_seconds = query_timeout_seconds or int(
            os.getenv("SQLSERVER_QUERY_TIMEOUT_SECONDS", "10")
        )
        self.max_rows = max(1, min(max_rows, 500))

    def run(self, diagnostic_name: str) -> dict[str, Any]:
        """Run one named diagnostic and return bounded rows as dictionaries."""
        # Live access must be explicitly enabled so a fresh clone cannot touch a
        # database by accident.
        if not self.enabled:
            raise RuntimeError("Live SQL diagnostics are disabled.")
        if not self.connection_string:
            raise RuntimeError("SQLSERVER_CONNECTION_STRING is not configured.")
        if diagnostic_name not in DIAGNOSTICS:
            raise ValueError(f"Unknown SQL diagnostic: {diagnostic_name}")

        diagnostic = DIAGNOSTICS[diagnostic_name]
        # Re-check the static template at execution time so future diagnostics
        # cannot accidentally bypass the read-only policy.
        assert_read_only_sql(diagnostic.query)

        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError("pyodbc is required for live SQL diagnostics.") from exc

        rows: list[dict[str, Any]] = []
        with pyodbc.connect(
            self.connection_string,
            timeout=5,
            readonly=True,
        ) as connection:
            cursor = connection.cursor()
            # Keep diagnostics responsive during incident triage and avoid long
            # blocking waits on production-like systems.
            cursor.timeout = self.query_timeout_seconds
            cursor.execute("SET LOCK_TIMEOUT 3000;")
            cursor.execute(diagnostic.query)
            columns = [column[0] for column in cursor.description]
            # Row limits prevent a diagnostic from returning huge result sets to
            # the UI or an MCP client.
            for row in cursor.fetchmany(self.max_rows):
                rows.append(dict(zip(columns, row)))

        return {
            "diagnostic": diagnostic.to_dict(include_query=False),
            "row_count": len(rows),
            "truncated": len(rows) == self.max_rows,
            "rows": rows,
        }
