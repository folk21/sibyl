"""Build-time machine-translation feature for validated curated passages.

It exports exact curated source passages for an explicit external large-LLM
translation step, validates returned generated text against the pinned source
identity, and exposes validated local translation artifacts to runtime corpus
assembly. Runtime translation and source acquisition remain outside this package.
"""

from .api import (
    export_translation_bundle,
    import_translation,
    load_validated_translation,
    load_validated_translation_from_documents,
    translation_source_curation_id,
    translation_source_passage_ids,
    validate_translation,
)

__all__ = [
    "export_translation_bundle",
    "import_translation",
    "load_validated_translation",
    "load_validated_translation_from_documents",
    "translation_source_curation_id",
    "translation_source_passage_ids",
    "validate_translation",
]
