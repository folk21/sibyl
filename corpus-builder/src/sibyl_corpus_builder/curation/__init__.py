"""Large-LLM curation feature for guided questions and literary passages.

The ``curation`` feature starts from the same prepared canonical sources used by
the automatic build, but it delegates semantic and literary judgment to an
external large language model at build time. It exports pinned canonical text
and stable guided questions, imports locator/hash proposals, and locally
revalidates every selected range before producing Git-safe curated metadata.

Pipeline position::

    prepared canonical sources + guided questions
        -> deterministic curation bundle
        -> external large LLM
        -> proposed ranges and question mappings
        -> local exact-text/hash validation
        -> validated curated metadata

The external model may decide relevance and natural passage boundaries, but it
is never authoritative for literary wording. Local canonical text, locators,
and hashes remain the source of truth. This feature does not perform runtime
network inference and does not replace the automatic ``build`` path for
arbitrary user questions.
"""

from .api import (
    export_curation_bundle,
    import_curation,
    load_question_catalog,
    validate_curated_curation,
)

__all__ = [
    "export_curation_bundle",
    "import_curation",
    "load_question_catalog",
    "validate_curated_curation",
]
