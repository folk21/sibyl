"""Public API for the large-LLM literary curation workflow.

Pipeline position:

    prepared canonical sources + stable guided questions
        -> export deterministic bundle
        -> external large LLM selects meaningful exact ranges
        -> import proposal
        -> local exact-text/hash validation
        -> Git-safe curated metadata
        -> validated exact slices for runtime-corpus assembly

The LLM decides literary relevance; local Python remains authoritative for canonical text
identity. Runtime code consumes only published corpus artifacts, never curation source files.
"""

from ._internal.bundle import export_curation_bundle
from ._internal.proposal import (
    curation_passage_ids,
    curation_source_keys,
    import_curation,
    load_validated_curation,
    load_validated_curation_from_documents,
    validate_curated_curation,
)
from ._internal.questions import load_question_catalog

__all__ = [
    "curation_passage_ids",
    "curation_source_keys",
    "export_curation_bundle",
    "import_curation",
    "load_question_catalog",
    "load_validated_curation",
    "load_validated_curation_from_documents",
    "validate_curated_curation",
]
