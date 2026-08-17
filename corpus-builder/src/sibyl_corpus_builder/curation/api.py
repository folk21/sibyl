"""Public API for the large-LLM literary curation workflow.

Pipeline position:

    prepared canonical sources + stable guided questions
        -> export deterministic bundle
        -> external large LLM selects meaningful exact ranges
        -> import proposal
        -> local exact-text/hash validation
        -> Git-safe curated metadata

The LLM decides literary relevance; local Python remains authoritative for canonical text
identity. Runtime consumption of curated mappings is intentionally a later feature boundary.
"""

from ._internal.bundle import export_curation_bundle
from ._internal.proposal import import_curation, validate_curated_curation
from ._internal.questions import load_question_catalog

__all__ = [
    "export_curation_bundle",
    "import_curation",
    "load_question_catalog",
    "validate_curated_curation",
]
