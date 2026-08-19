"""Large-LLM curation feature for guided questions and literary passages.

It exports prepared canonical texts plus stable guided questions, then imports
external locator/hash proposals and revalidates every selected range locally.
The LLM may decide relevance and natural boundaries, but canonical text,
locators, and hashes remain authoritative. The public API can also return
validated exact slices for build-time runtime-corpus assembly; runtime network
inference and direct curation-file reads remain outside this feature.
"""

from .api import (
    curation_source_keys,
    export_curation_bundle,
    import_curation,
    load_question_catalog,
    load_validated_curation,
    load_validated_curation_from_documents,
    validate_curated_curation,
)
from .models import (
    CuratedQuestionMatch,
    GuidedQuestion,
    QuestionCatalog,
    ValidatedCuratedPassage,
    ValidatedCuration,
)

__all__ = [
    "CuratedQuestionMatch",
    "GuidedQuestion",
    "QuestionCatalog",
    "ValidatedCuratedPassage",
    "ValidatedCuration",
    "curation_source_keys",
    "export_curation_bundle",
    "import_curation",
    "load_question_catalog",
    "load_validated_curation",
    "load_validated_curation_from_documents",
    "validate_curated_curation",
]
