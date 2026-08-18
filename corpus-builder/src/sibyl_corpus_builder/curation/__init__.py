"""Large-LLM curation feature for guided questions and literary passages.

It exports prepared canonical texts plus stable guided questions, then imports
external locator/hash proposals and revalidates every selected range locally.
The LLM may decide relevance and natural boundaries, but canonical text,
locators, and hashes remain authoritative. Runtime network inference and the
automatic generic-retrieval build are outside this feature."""

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
