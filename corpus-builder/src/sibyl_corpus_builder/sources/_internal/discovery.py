"""Source discovery orchestration that keeps catalog adapters separate from persistence."""

from pathlib import Path

from ..models import SelectionManifest
from .adapters import discover_source
from .selection import write_selection


def discover_to_file(url: str, output: Path) -> SelectionManifest:
    """Discovers a supported catalog and writes the editable developer-review manifest."""
    manifest = discover_source(url)
    write_selection(manifest, output)
    return manifest
