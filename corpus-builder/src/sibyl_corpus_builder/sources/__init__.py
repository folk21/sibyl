"""Source-ingestion feature for producing deterministic canonical input.

It owns discovery/registry resolution, reviewed acquisition/import,
source-specific normalization, raw/canonical caching, preparation, and optional
registration. Its public result is prepared canonical source data consumed by
``build`` or ``curation``; passage splitting, embeddings, and LLM proposal
processing do not belong here."""

from .api import (
    acquire_selection,
    discover_to_file,
    fetch_registry_source,
    import_registry_source,
    prepare_registry_sources,
    prepare_selection_sources,
    register_selection,
)

__all__ = [
    "acquire_selection",
    "discover_to_file",
    "fetch_registry_source",
    "import_registry_source",
    "prepare_registry_sources",
    "prepare_selection_sources",
    "register_selection",
]
