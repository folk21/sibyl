"""Public API for build-time large-LLM translation of validated curated passages.

Pipeline position:

    prepared foreign original + validated curation
        -> deterministic translation bundle
        -> external large LLM
        -> generated translation proposal
        -> local source/completeness/hash validation
        -> local validated translation artifact
        -> runtime corpus assembly

Generated translation text stays local build data. Runtime consumers see only persisted
``machine_translation`` text versions and never invoke a translation service.
"""

from ._internal.bundle import export_translation_bundle
from ._internal.proposal import (
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
