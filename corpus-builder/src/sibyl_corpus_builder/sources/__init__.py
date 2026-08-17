"""Source-ingestion feature: external text versions to canonical prepared input.

The ``sources`` feature owns the left side of the corpus pipeline. It discovers
or resolves concrete source versions, lets a developer review selections,
acquires or imports artifacts, runs source-specific normalization, caches raw
and canonical forms with hashes, and finally materializes a deterministic
prepared-source directory.

Pipeline position::

    catalog / registry / reviewed local file
        -> discover or resolve
        -> acquire / import
        -> normalize and cache
        -> prepare
        -> corpus-core SourceDocument values

The public facade exported from this package is intended for CLI composition
and other feature-neutral callers. Source-specific implementation details live
under ``adapters`` and feature-private orchestration lives under ``_internal``.
This feature does not split passages, compute embeddings, build runtime SQLite
artifacts, or perform large-LLM curation.
"""

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
