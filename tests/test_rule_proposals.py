"""Tests for unknown-incident rule proposal storage."""

import json
from pathlib import Path
import shutil

from src.rule_proposals import create_rule_proposal, is_actionable_adk_analysis


def test_adk_analysis_must_be_actionable_before_rule_proposal():
    """Skipped or failed ADK text should not unlock rule proposal saving."""
    assert is_actionable_adk_analysis("Likely cause: missing index") is True
    assert is_actionable_adk_analysis("ADK analysis failed; local result remains available.") is False
    assert is_actionable_adk_analysis("ADK analysis skipped because GOOGLE_API_KEY is not configured.") is False
    assert is_actionable_adk_analysis("") is False


def test_rule_proposal_is_saved_as_reviewable_json():
    """Rule proposals should be local JSON drafts, not active rules."""
    root = Path(".test-tmp") / "rule_proposals"
    if root.exists():
        shutil.rmtree(root)

    try:
        path = create_rule_proposal(
            proposal_dir=root,
            redacted_incident="Database: [REDACTED_DATABASE]\nUnknown incident",
            proposed_name="New Storage Rule",
            confirmed_category="Storage / Custom",
            confirmed_severity="High",
            candidate_keywords="storage wait, custom error",
            operator_notes="Reviewed after ADK analysis.",
            source_fingerprint="abc123",
        )

        saved = json.loads(Path(path).read_text(encoding="utf-8"))
        assert saved["status"] == "proposed"
        assert saved["name"] == "New Storage Rule"
        assert saved["candidate_keywords"] == ["storage wait", "custom error"]
        assert "SecretProductionDb" not in saved["redacted_incident"]
        assert "src/rules.py" in " ".join(saved["review_required"])
    finally:
        if root.exists():
            shutil.rmtree(root)
