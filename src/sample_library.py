"""Sample incident library helpers.

The sample library powers the demo dropdown and the optional user-approved
custom sample workflow. All custom samples are saved under `sample_incidents`
so they can be reused locally while remaining ignored by git.
"""

from __future__ import annotations

from pathlib import Path
import re


CUSTOM_SAMPLE_DIR_NAME = "custom"
# Bound saved data so an accidental large log paste does not create huge files.
MAX_SAVED_INCIDENT_CHARS = 12_000
MAX_SAVED_NOTES_CHARS = 4_000


def list_sample_names(sample_dir: Path) -> list[str]:
    """Return sample names relative to sample_dir, including custom samples."""
    root = sample_dir.resolve()
    names: list[str] = []
    for path in sorted(root.rglob("*.txt")):
        # Keep only regular text files; directories and other assets are not
        # valid incident samples.
        if not path.is_file():
            continue
        names.append(path.relative_to(root).as_posix())
    return names


def load_sample_text(sample_dir: Path, relative_name: str) -> str:
    """Read a sample by relative name while preventing path traversal."""
    root = sample_dir.resolve()
    path = (root / relative_name).resolve()
    # The resolved path must remain inside the sample directory even if a caller
    # provides `..` segments.
    if not _is_relative_to(path, root):
        raise ValueError("Sample path must stay inside the sample directory.")
    if path.suffix.lower() != ".txt" or not path.is_file():
        raise ValueError("Sample must be an existing .txt file.")
    return path.read_text(encoding="utf-8")


def is_actionable_adk_analysis(text: str | None) -> bool:
    """Return whether ADK output is useful enough to save with a custom sample."""
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


def create_custom_sample(
    sample_dir: Path,
    redacted_incident: str,
    confirmed_category: str,
    confirmed_severity: str,
    filename_hint: str,
    operator_notes: str = "",
    source_fingerprint: str = "",
) -> str:
    """Save a user-approved redacted sample and return its relative path."""
    # Saving is intentionally strict: empty samples are not useful, and custom
    # samples should contain a confirmed category/severity from human review.
    redacted = redacted_incident.strip()
    if not redacted:
        raise ValueError("Cannot save an empty incident sample.")

    category = confirmed_category.strip() or "Custom / Unclassified"
    severity = confirmed_severity.strip() or "Unknown"
    stem = _slugify(filename_hint or category)

    custom_dir = sample_dir / CUSTOM_SAMPLE_DIR_NAME
    custom_dir.mkdir(parents=True, exist_ok=True)

    # Use deterministic, readable filenames but avoid overwriting previous local
    # samples from separate incidents.
    path = _next_available_path(custom_dir, stem, source_fingerprint)
    content = _render_custom_sample(
        redacted_incident=redacted[:MAX_SAVED_INCIDENT_CHARS],
        confirmed_category=category,
        confirmed_severity=severity,
        operator_notes=operator_notes.strip()[:MAX_SAVED_NOTES_CHARS],
        source_fingerprint=source_fingerprint.strip(),
    )
    path.write_text(content, encoding="utf-8")
    return path.relative_to(sample_dir).as_posix()


def _render_custom_sample(
    redacted_incident: str,
    confirmed_category: str,
    confirmed_severity: str,
    operator_notes: str,
    source_fingerprint: str,
) -> str:
    """Render a custom sample as a human-readable text fixture."""
    notes = operator_notes or "No operator notes were provided."
    fingerprint = source_fingerprint or "not recorded"
    return f"""Custom SQL Server incident sample (redacted)

Confirmed category: {confirmed_category}
Confirmed severity: {confirmed_severity}
Source fingerprint: {fingerprint}

Incident:

{redacted_incident}

Verified notes / ADK analysis:

{notes}
"""


def _slugify(value: str) -> str:
    """Convert a user-provided filename/category into a safe sample stem."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug[:70] or "custom_incident"


def _next_available_path(
    directory: Path,
    stem: str,
    source_fingerprint: str,
) -> Path:
    """Find a non-conflicting file path for a custom sample."""
    candidate = directory / f"{stem}.txt"
    if not candidate.exists():
        return candidate

    suffix = _slugify(source_fingerprint)[:16]
    if suffix:
        candidate = directory / f"{stem}_{suffix}.txt"
        if not candidate.exists():
            return candidate

    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}.txt"
        if not candidate.exists():
            return candidate
        counter += 1


def _is_relative_to(path: Path, root: Path) -> bool:
    """Compatibility helper for checking whether one path is inside another."""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
