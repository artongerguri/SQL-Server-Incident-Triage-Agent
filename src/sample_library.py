from __future__ import annotations

from pathlib import Path
import re


CUSTOM_SAMPLE_DIR_NAME = "custom"
MAX_SAVED_INCIDENT_CHARS = 12_000
MAX_SAVED_NOTES_CHARS = 4_000


def list_sample_names(sample_dir: Path) -> list[str]:
    """Return sample names relative to sample_dir, including custom samples."""
    root = sample_dir.resolve()
    names: list[str] = []
    for path in sorted(root.rglob("*.txt")):
        if not path.is_file():
            continue
        names.append(path.relative_to(root).as_posix())
    return names


def load_sample_text(sample_dir: Path, relative_name: str) -> str:
    root = sample_dir.resolve()
    path = (root / relative_name).resolve()
    if not _is_relative_to(path, root):
        raise ValueError("Sample path must stay inside the sample directory.")
    if path.suffix.lower() != ".txt" or not path.is_file():
        raise ValueError("Sample must be an existing .txt file.")
    return path.read_text(encoding="utf-8")


def is_actionable_adk_analysis(text: str | None) -> bool:
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
    redacted = redacted_incident.strip()
    if not redacted:
        raise ValueError("Cannot save an empty incident sample.")

    category = confirmed_category.strip() or "Custom / Unclassified"
    severity = confirmed_severity.strip() or "Unknown"
    stem = _slugify(filename_hint or category)

    custom_dir = sample_dir / CUSTOM_SAMPLE_DIR_NAME
    custom_dir.mkdir(parents=True, exist_ok=True)

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
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug[:70] or "custom_incident"


def _next_available_path(
    directory: Path,
    stem: str,
    source_fingerprint: str,
) -> Path:
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
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
