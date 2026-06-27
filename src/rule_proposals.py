"""User-approved deterministic rule proposal storage.

Unknown incidents should not modify `src/rules.py` directly from the UI. This
module saves reviewed rule proposals as local JSON files so a DBA/developer can
later convert them into deterministic rules with tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


RULE_PROPOSAL_DIR = Path("data/rule_proposals")
MAX_TEXT_CHARS = 12_000
MAX_NOTES_CHARS = 4_000


def is_actionable_adk_analysis(text: str | None) -> bool:
    """Return whether ADK output is useful enough to support a rule proposal."""
    if not text:
        return False
    normalized = text.strip().lower()
    if not normalized:
        return False
    blocked_phrases = [
        "adk analysis skipped",
        "adk analysis failed",
        "adk completed without",
        "not requested",
        "not configured",
    ]
    return not any(phrase in normalized for phrase in blocked_phrases)


def create_rule_proposal(
    *,
    proposal_dir: Path = RULE_PROPOSAL_DIR,
    redacted_incident: str,
    proposed_name: str,
    confirmed_category: str,
    confirmed_severity: str,
    candidate_keywords: str,
    operator_notes: str,
    source_fingerprint: str,
) -> str:
    """Save a proposed rule as JSON and return its relative path."""
    incident = redacted_incident.strip()
    if not incident:
        raise ValueError("Cannot save a rule proposal without redacted incident text.")

    name = proposed_name.strip() or "Proposed SQL Server incident rule"
    category = confirmed_category.strip() or "Custom / Unclassified"
    severity = confirmed_severity.strip() or "Unknown"
    fingerprint = source_fingerprint.strip() or "not_recorded"

    proposal_dir.mkdir(parents=True, exist_ok=True)
    path = _next_available_path(proposal_dir, _slugify(name), fingerprint)

    proposal: dict[str, Any] = {
        "status": "proposed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_fingerprint": fingerprint,
        "name": name,
        "category": category,
        "severity": severity,
        "candidate_keywords": _split_keywords(candidate_keywords),
        "redacted_incident": incident[:MAX_TEXT_CHARS],
        "operator_notes": operator_notes.strip()[:MAX_NOTES_CHARS],
        "review_required": [
            "Validate category, severity, keywords, and likely cause.",
            "Confirm every SQL check is read-only.",
            "Add a TriageRule to src/rules.py only after human review.",
            "Add or update tests in tests/test_rules.py before publishing.",
        ],
    }
    path.write_text(json.dumps(proposal, indent=2, ensure_ascii=True), encoding="utf-8")
    return path.as_posix()


def _split_keywords(value: str) -> list[str]:
    """Parse comma/newline separated candidate keywords."""
    parts = re.split(r"[,\n]+", value)
    return [part.strip() for part in parts if part.strip()]


def _next_available_path(directory: Path, stem: str, source_fingerprint: str) -> Path:
    """Find a non-conflicting proposal filename."""
    candidate = directory / f"{stem}.json"
    if not candidate.exists():
        return candidate

    suffix = _slugify(source_fingerprint)[:16]
    if suffix:
        candidate = directory / f"{stem}_{suffix}.json"
        if not candidate.exists():
            return candidate

    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}.json"
        if not candidate.exists():
            return candidate
        counter += 1


def _slugify(value: str) -> str:
    """Convert a display name into a safe local JSON filename stem."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug[:70] or "proposed_rule"
