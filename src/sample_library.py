"""Sample incident library helpers.

The sample library powers the demo dropdown. Samples are static text fixtures
used for demos and tests; real users normally paste their own incident text.
"""

from __future__ import annotations

from pathlib import Path


def list_sample_names(sample_dir: Path) -> list[str]:
    """Return sample names relative to sample_dir."""
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


def _is_relative_to(path: Path, root: Path) -> bool:
    """Compatibility helper for checking whether one path is inside another."""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
