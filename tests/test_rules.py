from pathlib import Path

from src.rules import RULES, build_local_analysis
from src.security import is_read_only_sql


SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_incidents"


def test_disk_full_backup_is_critical():
    text = "Backup failed. Operating system error 112. There is not enough space on the disk."
    result = build_local_analysis(text)
    assert result["severity"] == "Critical"
    assert result["category"] == "Backup / Storage"


def test_active_transaction_is_detected():
    text = "log_reuse_wait_desc = ACTIVE_TRANSACTION. DBCC OPENTRAN shows oldest active transaction."
    result = build_local_analysis(text)
    assert result["severity"] == "Critical"
    assert result["category"] == "Transaction Log"


def test_replication_is_detected():
    text = "Replication subscription failed. Distribution agent cannot connect to subscriber."
    result = build_local_analysis(text)
    assert result["category"] == "Replication"


def test_deadlock_is_detected():
    result = build_local_analysis("Error 1205: transaction was deadlock victim")
    assert result["category"] == "Concurrency"
    assert result["severity"] == "High"


def test_unknown_incident_uses_safe_fallback():
    result = build_local_analysis("An unfamiliar SQL Server message")
    assert result["severity"] == "Unknown"
    assert result["matched_rules"] == []


def test_sample_incidents_classify_to_expected_categories():
    expected = {
        "active_transaction_log_full.txt": "Transaction Log",
        "backup_failed_disk_full.txt": "Backup / Storage",
        "deadlock_detected.txt": "Concurrency",
        "query_store_high_cpu.txt": "Performance",
        "replication_subscription_failed.txt": "Replication",
    }

    for filename, category in expected.items():
        result = build_local_analysis((SAMPLE_DIR / filename).read_text())
        assert result["category"] == category


def test_rule_sql_checks_are_read_only_templates():
    sql_checks = [
        sql_check
        for rule in RULES
        for sql_check in rule.sql_checks
    ]

    assert sql_checks
    assert all(is_read_only_sql(sql_check) for sql_check in sql_checks)
