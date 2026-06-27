"""Tests for sample incident listing and loading."""

from pathlib import Path
import shutil

from src.sample_library import list_sample_names, load_sample_text


def test_sample_names_include_nested_text_files():
    """Sample names should be relative paths below the sample directory."""
    root = Path(".test-tmp") / "sample_library"
    if root.exists():
        shutil.rmtree(root)

    try:
        (root / "existing.txt").parent.mkdir(parents=True, exist_ok=True)
        (root / "existing.txt").write_text("Existing sample", encoding="utf-8")
        (root / "nested").mkdir(parents=True, exist_ok=True)
        (root / "nested" / "incident.txt").write_text("Nested sample", encoding="utf-8")

        names = list_sample_names(root)
        assert "existing.txt" in names
        assert "nested/incident.txt" in names
        assert load_sample_text(root, "nested/incident.txt") == "Nested sample"
    finally:
        # Clean test output because `.test-tmp` is only a temporary workspace.
        if root.exists():
            shutil.rmtree(root)
