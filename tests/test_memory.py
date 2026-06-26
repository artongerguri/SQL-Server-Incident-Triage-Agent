"""Tests for redacted SQLite incident memory."""

from src.memory import IncidentMemoryStore
from src.rules import build_local_analysis


def test_memory_stores_only_redacted_incident():
    """Memory should persist the provided redacted preview, not raw secrets."""
    store = IncidentMemoryStore(":memory:")
    redacted = "Database: [REDACTED_DATABASE] backup failed disk full"
    analysis = build_local_analysis(redacted)

    memory_id = store.remember(redacted, analysis)
    records = store.recent()

    assert memory_id == records[0]["id"]
    assert records[0]["redacted_preview"] == redacted
    assert "SecretProductionDb" not in records[0]["redacted_preview"]


def test_memory_finds_similar_incidents():
    """Similarity search should return related incidents from the same category."""
    store = IncidentMemoryStore(":memory:")
    first = "backup failed because disk full on redacted volume"
    analysis = build_local_analysis(first)
    store.remember(first, analysis)

    matches = store.find_similar(
        "backup failed with disk full condition",
        category=analysis["category"],
    )

    assert matches
    assert matches[0]["similarity"] > 0
