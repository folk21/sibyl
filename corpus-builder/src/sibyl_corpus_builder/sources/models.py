"""Public data contracts for the source-ingestion feature.

These models describe the developer-reviewed selection boundary between source discovery and
acquisition. Source-family implementation details stay below ``sources.adapters`` and
``sources._internal``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SelectionWork:
    """Editable discovery result with an explicit include, exclude, or review decision."""

    id: str
    title: str
    source_url: str
    decision: str
    reason: str
    year: int | None = None
    genres: tuple[str, ...] = ()
    registry_work_id: str | None = None


@dataclass(frozen=True)
class SelectionManifest:
    """Developer-reviewed catalog selection consumed by later source-ingestion stages."""

    source_family: str
    source_url: str
    author: str
    language: str
    original_language: str
    category: str
    works: tuple[SelectionWork, ...]

    def included(self) -> tuple[SelectionWork, ...]:
        """Returns only works explicitly approved for this local acquisition batch."""
        return tuple(work for work in self.works if work.decision == "include")
