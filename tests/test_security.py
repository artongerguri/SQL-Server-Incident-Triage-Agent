"""Tests for privacy redaction and SQL allowlist behavior."""

import pytest

from src.security import assert_read_only_sql, is_read_only_sql, scan_and_redact


def test_sensitive_values_are_redacted():
    """Common SQL Server log secrets should be removed from external payloads."""
    text = """Database: Payroll
Server=prod-sql-01;User ID=admin;Password=secret123
Owner: admin@example.com
Client IP: 10.20.30.40
Executed as user: CONTOSO\\sqlagent
"""

    scan = scan_and_redact(text)

    for secret in [
        "Payroll",
        "prod-sql-01",
        "admin",
        "secret123",
        "admin@example.com",
        "10.20.30.40",
        "CONTOSO\\sqlagent",
    ]:
        assert secret not in scan.redacted_text
    assert len(scan.findings) >= 5


def test_input_is_limited_before_external_use():
    """Redaction also enforces a maximum incident payload size."""
    scan = scan_and_redact("x" * 20, max_chars=10)
    assert scan.redacted_text == "x" * 10
    assert scan.truncated is True


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT name FROM sys.databases;",
        "WITH waits AS (SELECT 1 AS value) SELECT * FROM waits;",
        "DBCC OPENTRAN('Demo');",
        "EXEC msdb.dbo.sp_help_jobhistory @mode = 'FULL';",
    ],
)
def test_read_only_sql_is_allowed(sql):
    """Reviewed diagnostic SQL templates should pass the allowlist."""
    assert is_read_only_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP DATABASE Demo;",
        "UPDATE dbo.Users SET IsAdmin = 1;",
        "SELECT * INTO dbo.CopyOfUsers FROM dbo.Users;",
        "EXEC xp_cmdshell 'whoami';",
        "DBCC SHRINKFILE(LogFile, 1);",
    ],
)
def test_dangerous_sql_is_blocked(sql):
    """Destructive or arbitrary SQL must be rejected by the guardrail."""
    assert not is_read_only_sql(sql)
    with pytest.raises(ValueError):
        assert_read_only_sql(sql)
