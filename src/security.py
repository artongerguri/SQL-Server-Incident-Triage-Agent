"""Privacy redaction and SQL safety validation.

This module contains the app's main security guardrails. Redaction protects
incident data before optional external AI use, while the SQL allowlist prevents
the project from acting like a general-purpose query runner.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Pattern


MAX_INCIDENT_CHARS = 20_000


@dataclass(frozen=True)
class PrivacyFinding:
    """Count of one sensitive-looking pattern found during redaction."""

    kind: str
    count: int


@dataclass(frozen=True)
class PrivacyScan:
    """Redacted text plus metadata needed for the UI privacy review panel."""

    redacted_text: str
    findings: list[PrivacyFinding]
    truncated: bool

    def to_dict(self) -> dict:
        return {
            "redacted_text": self.redacted_text,
            "findings": [asdict(finding) for finding in self.findings],
            "truncated": self.truncated,
        }


# Patterns are deliberately conservative and explainable. They target common
# values seen in SQL Server logs without trying to solve every possible PII case.
_REDACTION_PATTERNS: list[tuple[str, Pattern[str], str]] = [
    (
        "connection secret",
        re.compile(
            r"(?i)\b(password|pwd|access[ _-]?token|api[ _-]?key)\s*=\s*[^;\s]+"
        ),
        r"\1=[REDACTED]",
    ),
    (
        "email address",
        re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    (
        "IP address",
        re.compile(
            r"(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)"
            r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\d.])"
        ),
        "[REDACTED_IP]",
    ),
    (
        "user name",
        re.compile(
            r"(?im)\b(user id|uid|username|executed as user)\s*[:=]\s*([^;\r\n]+)"
        ),
        r"\1: [REDACTED_USER]",
    ),
    (
        "Windows account",
        re.compile(r"(?i)\b[A-Z0-9_.-]+\\[A-Z0-9_$.-]+\b"),
        "[REDACTED_ACCOUNT]",
    ),
    (
        "server name",
        re.compile(
            r"(?im)\b(server|data source|host|publisher|subscriber|distributor)"
            r"\s*[:=]\s*([^;\r\n]+)"
        ),
        r"\1: [REDACTED_SERVER]",
    ),
    (
        "database name",
        re.compile(r"(?im)\b(database|initial catalog)\s*[:=]\s*([^;\r\n]+)"),
        r"\1: [REDACTED_DATABASE]",
    ),
    (
        "UNC path",
        re.compile(r"\\\\[^\\\s]+\\[^\r\n\s]+"),
        r"\\[REDACTED_SERVER]\[REDACTED_PATH]",
    ),
]


def scan_and_redact(text: str, max_chars: int = MAX_INCIDENT_CHARS) -> PrivacyScan:
    # Redaction is the privacy boundary before optional external AI. The original
    # incident text is never required by ADK or by the local memory store.
    if not isinstance(text, str):
        raise TypeError("Incident input must be text.")
    if max_chars < 1:
        raise ValueError("max_chars must be positive.")

    truncated = len(text) > max_chars
    redacted = text[:max_chars]
    findings: list[PrivacyFinding] = []

    for kind, pattern, replacement in _REDACTION_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            findings.append(PrivacyFinding(kind=kind, count=count))

    return PrivacyScan(
        redacted_text=redacted,
        findings=findings,
        truncated=truncated,
    )


# Block write/destructive SQL verbs anywhere in the template before considering
# allowlisted read-only forms.
_FORBIDDEN_SQL = re.compile(
    r"(?i)\b(ALTER|BACKUP|CREATE|DELETE|DROP|INSERT|INTO|KILL|MERGE|RESTORE|"
    r"SHRINKDATABASE|SHRINKFILE|TRUNCATE|UPDATE)\b"
)
# EXEC is restricted because stored procedures can do anything. Only known
# read-only diagnostic procedures are accepted.
_ALLOWED_EXEC = {
    "xp_readerrorlog",
    "master.dbo.xp_readerrorlog",
    "msdb.dbo.sp_help_jobhistory",
    "sp_helppublication",
    "sp_helpsubscription",
}
# DBCC is also restricted to diagnostic commands used by this project.
_ALLOWED_DBCC = {"CHECKDB", "OPENTRAN", "SQLPERF"}


def is_read_only_sql(sql: str) -> bool:
    """Return whether a SQL template is allowed for manual/read-only diagnostics."""
    # Use an allowlist instead of trying to sanitize user-provided SQL. This app
    # exposes static templates for DBA review, not a general query runner.
    normalized = re.sub(r"--.*?$|/\*.*?\*/", " ", sql, flags=re.MULTILINE | re.DOTALL)
    normalized = re.sub(r"\s+", " ", normalized).strip().rstrip(";")
    if not normalized or _FORBIDDEN_SQL.search(normalized):
        return False

    first_word = normalized.split(" ", 1)[0].upper()
    if first_word in {"SELECT", "WITH"}:
        return True
    if first_word == "DBCC":
        match = re.match(r"(?i)^DBCC\s+([A-Z]+)", normalized)
        return bool(match and match.group(1).upper() in _ALLOWED_DBCC)
    if first_word in {"EXEC", "EXECUTE"}:
        match = re.match(r"(?i)^EXEC(?:UTE)?\s+([\w.]+)", normalized)
        return bool(match and match.group(1).lower() in _ALLOWED_EXEC)
    return False


def assert_read_only_sql(sql: str) -> None:
    """Raise when a SQL diagnostic template violates the allowlist."""
    if not is_read_only_sql(sql):
        raise ValueError("Only allowlisted read-only SQL diagnostics are permitted.")
