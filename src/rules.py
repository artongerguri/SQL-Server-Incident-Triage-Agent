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
        name="Transaction log autogrowth or VLF pressure",
        category="Transaction Log Growth",
        severity="High",
        keywords=[
            "log file autogrowth",
            "autogrow",
            "vlf",
            "virtual log file",
            "write log",
            "log write waits",
            "log file grew",
            "log growth",
        ],
        likely_cause="The transaction log is growing frequently or waiting on log writes because log sizing, disk latency, or workload volume is not aligned with the current transaction rate.",
        verification_steps=[
            "Check current log size and percent used.",
            "Review recent autogrowth messages in the SQL Server error log.",
            "Check log-related waits such as WRITELOG.",
            "Review transaction log backup cadence and disk latency before resizing.",
        ],
        recommended_actions=[
            "Do not shrink and regrow the log repeatedly.",
            "Right-size the log file after confirming normal workload requirements.",
            "Use fixed MB growth instead of small percentage growth.",
            "Review log backup cadence and storage performance.",
        ],
        sql_checks=[
            "DBCC SQLPERF(LOGSPACE);",
            "EXEC master.dbo.xp_readerrorlog;",
            "SELECT name, recovery_model_desc, log_reuse_wait_desc FROM sys.databases;",
            "SELECT wait_type, waiting_tasks_count, wait_time_ms FROM sys.dm_os_wait_stats WHERE wait_type = 'WRITELOG';",
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
        name="TempDB space pressure",
        category="TempDB",
        severity="Critical",
        keywords=[
            "tempdb",
            "could not allocate space",
            "error 1105",
            "version store",
            "snapshot isolation transaction aborted",
            "tempdb is full",
        ],
        likely_cause="TempDB is under space pressure because of user objects, internal objects, version store growth, or insufficient file capacity.",
        verification_steps=[
            "Check TempDB data and log file size, growth settings, and available volume space.",
            "Identify sessions consuming TempDB user or internal object pages.",
            "Check version store usage if snapshot isolation, online index work, or long transactions are active.",
            "Review recent jobs, large sorts, hash joins, reporting queries, and ETL workloads.",
        ],
        recommended_actions=[
            "Do not restart SQL Server before understanding whether a workload is still consuming TempDB.",
            "Add TempDB space only after confirming the underlying pressure and storage capacity.",
            "Tune or stop the workload consuming excessive TempDB after DBA approval.",
            "Review TempDB sizing, file count, and growth settings after the incident.",
        ],
        sql_checks=[
            "SELECT name, size, max_size, growth FROM tempdb.sys.database_files;",
            "SELECT session_id, user_objects_alloc_page_count, internal_objects_alloc_page_count FROM sys.dm_db_session_space_usage;",
            "SELECT session_id, user_objects_alloc_page_count, internal_objects_alloc_page_count FROM sys.dm_db_task_space_usage;",
        ],
    ),
    TriageRule(
        name="Blocking chain or lock wait",
        category="Blocking / Locks",
        severity="High",
        keywords=[
            "blocking",
            "blocked process",
            "blocking_session_id",
            "head blocker",
            "lck_m",
            "waitresource",
        ],
        likely_cause="One or more sessions are waiting on locks held by another transaction or long-running request.",
        verification_steps=[
            "Identify the head blocker and the blocked sessions.",
            "Check the wait type, wait resource, command, and elapsed time.",
            "Review the transaction scope and application workflow before taking action.",
            "Correlate the blocking with recent deployments, reports, imports, or maintenance jobs.",
        ],
        recommended_actions=[
            "Do not terminate a session without confirming business impact and rollback risk.",
            "Ask the application owner or DBA to approve any operational action.",
            "Reduce transaction duration and access objects in a consistent order.",
            "Add targeted indexes or query changes only after reviewing the execution plan.",
        ],
        sql_checks=[
            "SELECT session_id, status, command, wait_type, blocking_session_id, total_elapsed_time FROM sys.dm_exec_requests WHERE blocking_session_id <> 0;",
            "SELECT request_session_id, resource_type, request_mode, request_status FROM sys.dm_tran_locks;",
            "SELECT session_id, login_name, host_name, program_name, status FROM sys.dm_exec_sessions;",
        ],
    ),
    TriageRule(
        name="Database suspect or corruption signal",
        category="Database Integrity",
        severity="Critical",
        keywords=[
            "suspect",
            "recovery pending",
            "page checksum",
            "torn page",
            "error 823",
            "error 824",
            "error 825",
            "dbcc checkdb",
        ],
        likely_cause="SQL Server detected a database state or I/O integrity problem that may involve storage, page corruption, or incomplete recovery.",
        verification_steps=[
            "Check database state and recent SQL Server error log entries.",
            "Review suspect pages and storage or Windows event logs around the same timestamp.",
            "Run a safe DBCC CHECKDB validation in a controlled window or restored copy when possible.",
            "Confirm recent full, differential, and log backup availability before any repair action.",
        ],
        recommended_actions=[
            "Do not run repair options as a first response.",
            "Preserve evidence and validate backups before attempting recovery.",
            "Escalate to the DBA, storage, and infrastructure owners immediately.",
            "Prefer restore-based recovery over repair when business requirements allow it.",
        ],
        sql_checks=[
            "SELECT name, state_desc, user_access_desc FROM sys.databases WHERE state_desc <> 'ONLINE';",
            "SELECT database_id, file_id, page_id, event_type, error_count, last_update_date FROM msdb.dbo.suspect_pages;",
            "DBCC CHECKDB('YourDatabaseName') WITH NO_INFOMSGS, PHYSICAL_ONLY;",
        ],
    ),
    TriageRule(
        name="Login or authentication failure",
        category="Authentication / Access",
        severity="Medium",
        keywords=[
            "login failed",
            "error 18456",
            "cannot open database requested by the login",
            "sspi handshake failed",
            "untrusted domain",
            "login timeout",
        ],
        likely_cause="A login, default database, password, domain trust, or permission problem is preventing a user or application from connecting.",
        verification_steps=[
            "Check the SQL Server error log for the 18456 state code or SSPI message.",
            "Confirm whether the login is disabled, locked, expired, or mapped to the right database.",
            "Check the login default database and whether the target database is online.",
            "Confirm whether the error affects one user, one application, or all connections.",
        ],
        recommended_actions=[
            "Do not reset credentials until the exact login and failure state are confirmed.",
            "Use the 18456 state code to distinguish password, disabled login, default database, and permission issues.",
            "Coordinate with identity or domain administrators for SSPI or trust failures.",
            "Document the affected application, host, and login before changing access.",
        ],
        sql_checks=[
            "EXEC master.dbo.xp_readerrorlog;",
            "SELECT name, is_disabled, type_desc, default_database_name FROM sys.sql_logins;",
            "SELECT name, state_desc, user_access_desc FROM sys.databases;",
        ],
    ),
    TriageRule(
        name="Always On availability group health issue",
        category="High Availability",
        severity="Critical",
        keywords=[
            "availability group",
            "always on",
            "not synchronizing",
            "synchronization health",
            "redo queue",
            "log send queue",
            "replica disconnected",
            "hadron",
        ],
        likely_cause="An Always On availability group replica or database is unhealthy because of connectivity, synchronization lag, queue growth, or failover state.",
        verification_steps=[
            "Check replica role, connected state, and synchronization health.",
            "Review database-level synchronization state, log send queue, and redo queue.",
            "Confirm network, listener, endpoint, and cluster health around the incident time.",
            "Identify whether the issue affects one database, one replica, or the entire availability group.",
        ],
        recommended_actions=[
            "Do not force failover until data loss risk and quorum state are understood.",
            "Check whether the secondary is catching up before taking disruptive action.",
            "Escalate to DBA and infrastructure owners if the primary or quorum is unstable.",
            "Review recent network, storage, or patching changes after service is stable.",
        ],
        sql_checks=[
            "SELECT ag.name, ar.replica_server_name, ars.role_desc, ars.connected_state_desc, ars.synchronization_health_desc FROM sys.availability_groups AS ag INNER JOIN sys.availability_replicas AS ar ON ag.group_id = ar.group_id INNER JOIN sys.dm_hadr_availability_replica_states AS ars ON ar.replica_id = ars.replica_id;",
            "SELECT DB_NAME(database_id) AS database_name, synchronization_state_desc, synchronization_health_desc, log_send_queue_size, redo_queue_size FROM sys.dm_hadr_database_replica_states;",
        ],
    ),
    TriageRule(
        name="Backup chain or recovery point risk",
        category="Backup / Recovery",
        severity="High",
        keywords=[
            "backup chain",
            "log backup",
            "differential base",
            "no recent backup",
            "last log backup",
            "recovery point objective",
            "rpo",
        ],
        likely_cause="The database may not meet recovery objectives because recent full, differential, or log backups are missing, delayed, or not aligned.",
        verification_steps=[
            "Review recent backup history for the affected database.",
            "Check whether full, differential, and log backup cadence matches the recovery objective.",
            "Confirm backup job status and storage availability.",
            "Validate that backup files are accessible and restorable in a safe environment.",
        ],
        recommended_actions=[
            "Do not assume recovery is possible until backup history and files are verified.",
            "Fix failed backup jobs and storage issues before the next maintenance window.",
            "Run a restore test in a non-production environment when possible.",
            "Update monitoring to alert on missing or stale backups.",
        ],
        sql_checks=[
            "SELECT TOP (50) database_name, type, backup_start_date, backup_finish_date, is_copy_only FROM msdb.dbo.backupset ORDER BY backup_finish_date DESC;",
            "SELECT name, recovery_model_desc, state_desc FROM sys.databases;",
            "EXEC msdb.dbo.sp_help_jobhistory @mode = 'FULL';",
        ],
    ),
    TriageRule(
        name="Memory pressure or query grant starvation",
        category="Memory Pressure",
        severity="High",
        keywords=[
            "memory pressure",
            "out of memory",
            "resource_semaphore",
            "page life expectancy",
            "insufficient system memory",
            "error 701",
            "error 802",
        ],
        likely_cause="SQL Server is under memory pressure or queries are waiting for memory grants, causing slow response or failed allocations.",
        verification_steps=[
            "Check memory-related waits and pending memory grants.",
            "Review Page Life Expectancy and memory clerk distribution.",
            "Identify large queries requesting memory grants.",
            "Check whether the issue started after a workload change, deployment, or configuration change.",
        ],
        recommended_actions=[
            "Do not change max server memory during an incident without understanding OS pressure.",
            "Identify and tune queries with excessive memory grants.",
            "Review indexes, statistics, and query plans for large sorts or hashes.",
            "Validate SQL Server and OS memory configuration after immediate pressure is resolved.",
        ],
        sql_checks=[
            "SELECT wait_type, waiting_tasks_count, wait_time_ms FROM sys.dm_os_wait_stats WHERE wait_type LIKE 'RESOURCE_SEMAPHORE%';",
            "SELECT type, pages_kb FROM sys.dm_os_memory_clerks ORDER BY pages_kb DESC;",
            "SELECT session_id, requested_memory_kb, granted_memory_kb, required_memory_kb FROM sys.dm_exec_query_memory_grants;",
        ],
    ),
    TriageRule(
        name="Connectivity or timeout issue",
        category="Connectivity",
        severity="High",
        keywords=[
            "timeout expired",
            "connection timeout",
            "transport-level error",
            "forcibly closed",
            "pre-login handshake",
            "connection pool",
            "network-related",
        ],
        likely_cause="Applications are failing to connect or complete requests because of network, listener, SQL Server availability, pool exhaustion, or login latency.",
        verification_steps=[
            "Determine whether the issue affects all clients or only one application/server.",
            "Check SQL Server error log for login, network, or failover messages.",
            "Review active sessions and connection counts by host and program.",
            "Correlate with network, firewall, DNS, listener, or application deployment changes.",
        ],
        recommended_actions=[
            "Do not assume the database engine is the root cause before checking network and application layers.",
            "Verify listener or instance name resolution from the affected client network.",
            "Coordinate with application owners if connection pool exhaustion is suspected.",
            "Escalate to infrastructure teams if errors align with network or firewall changes.",
        ],
        sql_checks=[
            "EXEC master.dbo.xp_readerrorlog;",
            "SELECT session_id, login_name, host_name, program_name, status FROM sys.dm_exec_sessions;",
            "SELECT client_net_address, local_net_address, local_tcp_port FROM sys.dm_exec_connections;",
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
