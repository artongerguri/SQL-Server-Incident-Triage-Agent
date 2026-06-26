"""Redacted local incident memory.

The memory store supports useful demo behavior without storing original logs.
It persists only redacted previews and classification metadata, which keeps the
feature aligned with the app's privacy model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class IncidentMemory:
    """Serializable record stored in the local SQLite memory database."""

    id: int
    created_at: str
    fingerprint: str
    category: str
    severity: str
    redacted_preview: str
    matched_rule_names: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class IncidentMemoryStore:
    """SQLite memory that never accepts or stores the original incident text."""

    def __init__(self, path: str | Path | None = None):
        # Environment configuration keeps the app deployable while tests can use
        # `:memory:` for isolated in-process databases.
        configured_path = path or os.getenv("INCIDENT_MEMORY_PATH", "data/incidents.db")
        self.path = Path(configured_path)
        self._memory_connection: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Open SQLite and ensure the memory table exists."""
        if str(self.path) == ":memory:":
            # Reuse the same in-memory connection so data survives across
            # multiple method calls during a single test.
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(":memory:")
            connection = self._memory_connection
        else:
            # File-backed memory creates its parent folder lazily for local demos.
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incident_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                fingerprint TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                redacted_preview TEXT NOT NULL,
                matched_rule_names TEXT NOT NULL
            )
            """
        )
        return connection

    def remember(self, redacted_text: str, analysis: dict) -> int:
        """Insert or update one redacted incident memory record."""
        # Fingerprinting redacted text deduplicates repeated incidents without
        # storing the original sensitive input.
        fingerprint = hashlib.sha256(redacted_text.encode("utf-8")).hexdigest()
        matched_rule_names = [
            rule.get("name", "Unknown rule")
            for rule in analysis.get("matched_rules", [])
        ]
        created_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO incident_memory (
                    created_at, fingerprint, category, severity,
                    redacted_preview, matched_rule_names
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    created_at = excluded.created_at,
                    category = excluded.category,
                    severity = excluded.severity,
                    redacted_preview = excluded.redacted_preview,
                    matched_rule_names = excluded.matched_rule_names
                """,
                (
                    created_at,
                    fingerprint,
                    analysis.get("category", "General SQL Server Incident"),
                    analysis.get("severity", "Unknown"),
                    redacted_text[:500],
                    json.dumps(matched_rule_names),
                ),
            )
            row = connection.execute(
                "SELECT id FROM incident_memory WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
        return int(row["id"])

    def recent(self, limit: int = 10, category: str | None = None) -> list[dict]:
        """Return recent memory records, optionally scoped to a category."""
        # Bound the limit so a UI or MCP caller cannot request unbounded rows.
        safe_limit = max(1, min(limit, 100))
        query = "SELECT * FROM incident_memory"
        params: list[object] = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(safe_limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_memory(row).to_dict() for row in rows]

    def find_similar(self, redacted_text: str, category: str, limit: int = 5) -> list[dict]:
        """Find category-matched memories using simple token overlap."""
        # This lightweight similarity score is deterministic, local, and easy to
        # explain in a capstone demo.
        candidates = self.recent(limit=50, category=category)
        query_tokens = _tokens(redacted_text)
        scored: list[tuple[float, dict]] = []
        for candidate in candidates:
            candidate_tokens = _tokens(candidate["redacted_preview"])
            union = query_tokens | candidate_tokens
            score = len(query_tokens & candidate_tokens) / len(union) if union else 0.0
            if score:
                item = {**candidate, "similarity": round(score, 3)}
                scored.append((score, item))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in scored[: max(1, min(limit, 20))]]

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> IncidentMemory:
        """Convert a SQLite row into the dataclass used by callers."""
        return IncidentMemory(
            id=row["id"],
            created_at=row["created_at"],
            fingerprint=row["fingerprint"],
            category=row["category"],
            severity=row["severity"],
            redacted_preview=row["redacted_preview"],
            matched_rule_names=json.loads(row["matched_rule_names"]),
        )


def _tokens(text: str) -> set[str]:
    """Tokenize redacted incident text for local similarity search."""
    return {
        token.lower()
        for token in text.replace("_", " ").split()
        if len(token) >= 4 and not token.startswith("[REDACTED")
    }
