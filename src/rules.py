from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Iterable


@dataclass
class TriageRule:
    name: str
    category: str
    severity: str
    keywords: list[str]
    likely_cause: str
    verification_steps: list[str]
    recommended_actions: list[str]
    sql_checks: list[str]


RULES: list[TriageRule] = [
    TriageRule(
        name="Disk full during backup or log growth",
        category="Backup / Storage",
        severity="Critical",
        keywords=["disk full", "not enough space", "operating system error 112", "backup failed", "insufficient disk space"],
        likely_cause="The SQL Server backup or database log operation cannot complete because the target disk or log disk has insufficient free space.",
        verification_steps=[
            "Check free space on the backup destination and database log drive.",
            "Check SQL Agent job history for the failed backup step.",
            "Check SQL Server error log around the backup failure time.",
            "Confirm whether other files or old backups are consuming the target volume.",
        ],
        recommended_actions=[
            "Free disk space by moving or deleting old backup files according to retention policy.",
            "Run a fresh backup after space is available.",
            "If transaction log is full, identify why log reuse is blocked before attempting shrink.",
            "Add monitoring alerts for low free space on backup and log volumes.",
        ],
        sql_checks=[
            "EXEC msdb.dbo.sp_help_jobhistory @mode = 'FULL';",
            "SELECT name, recovery_model_desc, log_reuse_wait_desc FROM sys.databases;",
            "DBCC SQLPERF(LOGSPACE);",
        ],
    ),
    TriageRule(
        name="Log reuse blocked by active transaction",
        category="Transaction Log",
        severity="Critical",
        keywords=["active_transaction", "log_reuse_wait_desc", "dbcc opentran", "oldest active transaction", "transaction log is full"],
        likely_cause="Transaction log reuse is blocked by a long-running or orphaned active transaction.",
        verification_steps=[
            "Run DBCC OPENTRAN for the affected database.",
            "Check sys.databases.log_reuse_wait_desc.",
            "Identify active requests and sessions related to the oldest transaction.",
            "Check whether SQL Agent jobs, replication, imports, or application sessions are holding the transaction open.",
        ],
        recommended_actions=[
            "Do not shrink the log before log reuse is possible.",
            "Identify and safely stop or complete the session/job holding the transaction.",
            "Take a full backup if required by the backup strategy.",
            "After log reuse is clear, shrink only if there is a one-time emergency and you understand the impact.",
        ],
        sql_checks=[
            "DBCC OPENTRAN('YourDatabaseName');",
            "SELECT name, log_reuse_wait_desc FROM sys.databases WHERE name = 'YourDatabaseName';",
            "SELECT session_id, status, command, wait_type, blocking_session_id FROM sys.dm_exec_requests;",
            "SELECT * FROM sys.dm_tran_database_transactions;",
        ],
    ),
    TriageRule(
        name="Replication subscription or linked server failure",
        category="Replication",
        severity="High",
        keywords=["replication", "subscription", "publication", "linked server", "distribution agent", "log reader agent", "subscriber"],
        likely_cause="Replication is failing because an agent, linked server, permission, schema object, or subscription configuration is invalid or unavailable.",
        verification_steps=[
            "Check Replication Monitor for failing agents.",
            "Check SQL Agent jobs related to Log Reader, Snapshot, Distribution, or Merge agents.",
            "Confirm publisher, distributor, and subscriber connectivity.",
            "Validate object names, primary keys, and article configuration.",
        ],
        recommended_actions=[
            "Fix connectivity or linked server configuration first.",
            "Restart the failing replication agent after correcting the root cause.",
            "If an article/table was renamed, update the publication/subscription configuration.",
            "Avoid dropping/recreating replication until the exact failing component is identified.",
        ],
        sql_checks=[
            "EXEC sp_helppublication;",
            "EXEC sp_helpsubscription;",
            "SELECT * FROM msdb.dbo.sysjobs WHERE name LIKE '%Log Reader%' OR name LIKE '%Distribution%';",
        ],
    ),
    TriageRule(
        name="SQL Agent job or maintenance plan failure",
        category="SQL Agent / Maintenance Plan",
        severity="High",
        keywords=["sqlserveragent", "maintenance plan", "job failed", "step failed", "ssis", "execute sql task", "0xc00291ec"],
        likely_cause="A SQL Agent job or SSIS Maintenance Plan step failed because of connection, permission, path, package, or SQL execution problems.",
        verification_steps=[
            "Read the complete SQL Agent job history, not only the summary line.",
            "Identify the exact failing step.",
            "Check the SQL Agent service account permissions.",
            "Verify backup path availability and local/server connection configuration.",
        ],
        recommended_actions=[
            "Fix the failing step instead of recreating the whole Maintenance Plan immediately.",
            "Confirm that the SQL Agent service account can access the target folder.",
            "Test the backup command manually with a small database if needed.",
            "If the package is corrupted, recreate the Maintenance Plan step cleanly.",
        ],
        sql_checks=[
            "EXEC msdb.dbo.sp_help_jobhistory @mode = 'FULL';",
            "SELECT name, enabled, date_created, date_modified FROM msdb.dbo.sysjobs ORDER BY date_modified DESC;",
        ],
    ),
    TriageRule(
        name="Query Store or high CPU workload",
        category="Performance",
        severity="Medium",
        keywords=["query store", "high cpu", "slow query", "duration", "logical reads", "execution plan", "regressed query"],
        likely_cause="A query or workload is consuming high CPU, reads, or duration. Query Store can help identify top resource-consuming queries.",
        verification_steps=[
            "Check Query Store top resource consumers.",
            "Compare recent plans with previous good plans.",
            "Review index usage and missing indexes carefully.",
            "Check whether the issue started after deployment, statistics changes, or parameter sniffing.",
        ],
        recommended_actions=[
            "Identify the top query by CPU/duration/reads.",
            "Review execution plan before applying indexes.",
            "Avoid forcing plans without testing.",
            "Use Query Store only with a storage cap and monitoring.",
        ],
        sql_checks=[
            "SELECT actual_state_desc, desired_state_desc, current_storage_size_mb, max_storage_size_mb FROM sys.database_query_store_options;",
            "SELECT TOP (20) * FROM sys.query_store_runtime_stats ORDER BY avg_cpu_time DESC;",
        ],
    ),
    TriageRule(
        name="Deadlock detected",
        category="Concurrency",
        severity="High",
        keywords=["deadlock", "victim", "1205", "deadlock graph"],
        likely_cause="Two or more sessions are blocking each other and SQL Server selected one as the deadlock victim.",
        verification_steps=[
            "Check Extended Events system_health for deadlock graph.",
            "Identify the tables, indexes, and statements involved.",
            "Check transaction scope and lock order.",
        ],
        recommended_actions=[
            "Keep transactions short.",
            "Access objects in consistent order.",
            "Review indexes for the involved queries.",
            "Add retry logic at application level if appropriate.",
        ],
        sql_checks=[
            "SELECT XEvent.query('.') AS DeadlockGraph FROM (SELECT CAST(target_data AS XML) AS TargetData FROM sys.dm_xe_session_targets st JOIN sys.dm_xe_sessions s ON s.address = st.event_session_address WHERE s.name = 'system_health' AND st.target_name = 'ring_buffer') AS Data CROSS APPLY TargetData.nodes('//RingBufferTarget/event[@name=\"xml_deadlock_report\"]') AS XEventData(XEvent);",
        ],
    ),
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def match_rules(text: str) -> list[dict]:
    normalized = normalize_text(text)
    matched: list[dict] = []

    for rule in RULES:
        hits = [kw for kw in rule.keywords if kw.lower() in normalized]
        if hits:
            item = asdict(rule)
            item["matched_keywords"] = hits
            item["score"] = len(hits)
            matched.append(item)

    matched.sort(key=lambda item: item["score"], reverse=True)
    return matched


def choose_severity(matched_rules: Iterable[dict]) -> str:
    severity_rank = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
        "Unknown": 0,
    }

    best = "Unknown"
    for rule in matched_rules:
        sev = rule.get("severity", "Unknown")
        if severity_rank.get(sev, 0) > severity_rank.get(best, 0):
            best = sev
    return best


def build_local_analysis(text: str) -> dict:
    matched = match_rules(text)

    if not matched:
        return {
            "category": "General SQL Server Incident",
            "severity": "Unknown",
            "likely_cause": "No specific rule matched. Review the full SQL Server error log, SQL Agent history, and recent changes.",
            "verification_steps": [
                "Collect the complete error message and timestamp.",
                "Check SQL Server error log.",
                "Check SQL Agent job history.",
                "Identify database, server, and application involved.",
            ],
            "recommended_actions": [
                "Do not run destructive commands without understanding the root cause.",
                "Reproduce or isolate the issue in a safe environment if possible.",
                "Add the new incident pattern to src/rules.py for future matching.",
            ],
            "sql_checks": [
                "EXEC xp_readerrorlog;",
                "EXEC msdb.dbo.sp_help_jobhistory @mode = 'FULL';",
            ],
            "matched_rules": [],
        }

    primary = matched[0]

    verification_steps = []
    recommended_actions = []
    sql_checks = []

    for rule in matched:
        verification_steps.extend(rule["verification_steps"])
        recommended_actions.extend(rule["recommended_actions"])
        sql_checks.extend(rule["sql_checks"])

    return {
        "category": primary["category"],
        "severity": choose_severity(matched),
        "likely_cause": primary["likely_cause"],
        "verification_steps": list(dict.fromkeys(verification_steps)),
        "recommended_actions": list(dict.fromkeys(recommended_actions)),
        "sql_checks": list(dict.fromkeys(sql_checks)),
        "matched_rules": matched,
    }
