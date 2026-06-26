"""Tests for deterministic SQL Server incident rules."""

from pathlib import Path

from src.rules import RULES, build_local_analysis
from src.security import is_read_only_sql


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_incidents"


def test_disk_full_backup_is_critical():
    """Disk-space backup failures should be treated as critical."""
    text = "Backup failed. Operating system error 112. There is not enough space on the disk."
    result = build_local_analysis(text)
    assert result["severity"] == "Critical"
    assert result["category"] == "Backup / Storage"


def test_active_transaction_is_detected():
    """ACTIVE_TRANSACTION should map to transaction log triage."""
    text = "log_reuse_wait_desc = ACTIVE_TRANSACTION. DBCC OPENTRAN shows oldest active transaction."
    result = build_local_analysis(text)
    assert result["severity"] == "Critical"
    assert result["category"] == "Transaction Log"


def test_replication_is_detected():
    """Replication terms should select the replication category."""
    text = "Replication subscription failed. Distribution agent cannot connect to subscriber."
    result = build_local_analysis(text)
    assert result["category"] == "Replication"


def test_deadlock_is_detected():
    """Deadlock victim errors should classify as concurrency incidents."""
    result = build_local_analysis("Error 1205: transaction was deadlock victim")
    assert result["category"] == "Concurrency"
    assert result["severity"] == "High"


def test_tempdb_pressure_is_detected():
    """TempDB allocation failures should be critical TempDB incidents."""
    result = build_local_analysis("Error 1105: tempdb is full and version store is growing")
    assert result["category"] == "TempDB"
    assert result["severity"] == "Critical"


def test_database_integrity_issue_is_detected():
    """Checksum or suspect database signals should be critical integrity issues."""
    result = build_local_analysis("Error 824 page checksum database is suspect")
    assert result["category"] == "Database Integrity"
    assert result["severity"] == "Critical"


def test_high_availability_issue_is_detected():
    """Always On synchronization symptoms should map to HA triage."""
    result = build_local_analysis("Always On availability group is not synchronizing and redo queue is growing")
    assert result["category"] == "High Availability"
    assert result["severity"] == "Critical"


def test_connectivity_issue_is_detected():
    """Pre-login and transport errors should map to connectivity triage."""
    result = build_local_analysis("Pre-login handshake timeout expired with transport-level error")
    assert result["category"] == "Connectivity"
    assert result["severity"] == "High"


def test_transaction_log_growth_issue_is_detected():
    """Log autogrowth and WRITELOG symptoms should map to log growth triage."""
    result = build_local_analysis("Transaction log file autogrowth caused WRITELOG waits and high VLF count")
    assert result["category"] == "Transaction Log Growth"
    assert result["severity"] == "High"


def test_unknown_incident_uses_safe_fallback():
    """Unknown incidents should still produce safe general guidance."""
    result = build_local_analysis("An unfamiliar SQL Server message")
    assert result["severity"] == "Unknown"
    assert result["matched_rules"] == []


def test_sample_incidents_classify_to_expected_categories():
    """Every checked-in sample should demonstrate the expected incident category."""
    expected = {
        "active_transaction_log_full.txt": "Transaction Log",
        "always_on_not_synchronizing.txt": "High Availability",
        "backup_failed_disk_full.txt": "Backup / Storage",
        "backup_chain_rpo_risk.txt": "Backup / Recovery",
        "blocking_chain_lck_m_waits.txt": "Blocking / Locks",
        "connectivity_prelogin_timeout.txt": "Connectivity",
        "database_suspect_page_checksum.txt": "Database Integrity",
        "deadlock_detected.txt": "Concurrency",
        "login_failed_18456.txt": "Authentication / Access",
        "memory_pressure_resource_semaphore.txt": "Memory Pressure",
        "query_store_high_cpu.txt": "Performance",
        "replication_subscription_failed.txt": "Replication",
        "tempdb_space_pressure.txt": "TempDB",
        "transaction_log_autogrowth_vlf_pressure.txt": "Transaction Log Growth",
    }

    for filename, category in expected.items():
        # This guards the public demo library from drifting away from the rules.
        result = build_local_analysis((SAMPLE_DIR / filename).read_text())
        assert result["category"] == category


def test_rule_sql_checks_are_read_only_templates():
    """All rule-provided SQL checks must remain safe templates."""
    sql_checks = [
        sql_check
        for rule in RULES
        for sql_check in rule.sql_checks
    ]

    assert sql_checks
    assert all(is_read_only_sql(sql_check) for sql_check in sql_checks)
