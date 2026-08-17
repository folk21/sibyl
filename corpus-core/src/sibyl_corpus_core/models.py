"""Shared canonical-source contracts used after source preparation.

Pipeline position:

    external source -> source-specific preparation -> SourceDocument
                                                -> automatic corpus build
                                                -> LLM curation

The types in this module intentionally know nothing about acquisition sites, embeddings,
LLM proposal formats, or the persisted runtime corpus schema. They are the narrow boundary
between source ingestion and downstream corpus-processing features.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
    """Canonical source text plus provenance needed by downstream corpus features.

    ``text`` is the canonical literary text. Downstream code may select exact character
    ranges from it, but must not rewrite the stored wording. ``canonical_text_sha256`` pins
    the prepared version when source preparation can provide that hash.
    """

    source_id: str
    text_version_id: str
    author: str
    work: str
    text: str
    source_name: str
    language: str
    original_language: str
    category: str
    text_role: str
    translator: str | None = None
    translation_provider: str | None = None
    translation_model: str | None = None
    source_uri: str | None = None
    source_locator: str | None = None
    source_artifact_sha256: str | None = None
    canonical_text_sha256: str | None = None
    rights_status: str | None = None
    rights_jurisdiction: str | None = None
    provenance: str | None = None
