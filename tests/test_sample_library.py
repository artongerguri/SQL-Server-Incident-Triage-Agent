"""Tests for sample incident listing, loading, and custom sample creation."""

from pathlib import Path
import shutil

from src.sample_library import (
    create_custom_sample,
    is_actionable_adk_analysis,
    list_sample_names,
    load_sample_text,
)


def test_adk_analysis_must_be_actionable_before_sample_save():
    """Skipped or failed ADK text should not unlock custom sample saving."""
    assert is_actionable_adk_analysis("Likely cause: missing index") is True
    assert is_actionable_adk_analysis("ADK analysis failed; local result remains available.") is False
    assert is_actionable_adk_analysis("ADK analysis skipped because GOOGLE_API_KEY is not configured.") is False
    assert is_actionable_adk_analysis("") is False


def test_custom_sample_is_saved_under_custom_directory():
    """Custom samples should be saved safely below `sample_incidents/custom`."""
    root = Path(".test-tmp") / "sample_library"
    if root.exists():
        shutil.rmtree(root)

    try:
        # Create one existing root-level sample so listing covers both standard
        # and custom sample paths.
        (root / "existing.txt").parent.mkdir(parents=True, exist_ok=True)
        (root / "existing.txt").write_text("Existing sample", encoding="utf-8")

        relative_name = create_custom_sample(
            sample_dir=root,
            redacted_incident="Database: [REDACTED_DATABASE]\nUnknown storage incident",
            confirmed_category="Storage / Custom",
            confirmed_severity="High",
            filename_hint="Storage Incident!",
            operator_notes="Verified safe workaround after DBA review.",
            source_fingerprint="abc123",
        )

        assert relative_name == "custom/storage_incident.txt"
        saved_text = (root / relative_name).read_text(encoding="utf-8")
        assert "Database: [REDACTED_DATABASE]" in saved_text
        assert "Storage / Custom" in saved_text
        assert "Verified safe workaround" in saved_text
        assert "SecretProductionDb" not in saved_text

        names = list_sample_names(root)
        assert "existing.txt" in names
        assert "custom/storage_incident.txt" in names
        assert load_sample_text(root, relative_name) == saved_text
    finally:
        # Clean test output because `.test-tmp` is only a temporary workspace.
        if root.exists():
            shutil.rmtree(root)
