"""Source discovery orchestration that keeps catalog adapters separate from persistence."""

from pathlib import Path

from ..models import SelectionManifest
from .adapters import discover_source
from .selection import write_selection


def discover_to_file(
    url: str,
    output: Path,
    *,
    language: str | None = None,
    original_language: str | None = None,
) -> SelectionManifest:
    """Discovers a catalog with optional language overrides and writes the review manifest."""
    manifest = discover_source(
        url,
        language=language,
        original_language=original_language,
    )
    write_selection(manifest, output)
    return manifest
