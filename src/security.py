from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Pattern


MAX_INCIDENT_CHARS = 20_000


@dataclass(frozen=True)
class PrivacyFinding:
    kind: str
    count: int


@dataclass(frozen=True)
class PrivacyScan:
    redacted_text: str
    findings: list[PrivacyFinding]
    truncated: bool

    def to_dict(self) -> dict:
        return {
            "redacted_text": self.redacted_text,
            "findings": [asdict(finding) for finding in self.findings],
            "truncated": self.truncated,
        }


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


_FORBIDDEN_SQL = re.compile(
    r"(?i)\b(ALTER|BACKUP|CREATE|DELETE|DROP|INSERT|INTO|KILL|MERGE|RESTORE|"
    r"SHRINKDATABASE|SHRINKFILE|TRUNCATE|UPDATE)\b"
)
_ALLOWED_EXEC = {
    "xp_readerrorlog",
    "master.dbo.xp_readerrorlog",
    "msdb.dbo.sp_help_jobhistory",
    "sp_helppublication",
    "sp_helpsubscription",
}
_ALLOWED_DBCC = {"OPENTRAN", "SQLPERF"}


def is_read_only_sql(sql: str) -> bool:
    """Return whether a SQL template is allowed for manual/read-only diagnostics."""
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
    if not is_read_only_sql(sql):
        raise ValueError("Only allowlisted read-only SQL diagnostics are permitted.")
