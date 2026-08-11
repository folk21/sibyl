from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
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
    rights_status: str | None = None
    rights_jurisdiction: str | None = None
    provenance: str | None = None


@dataclass(frozen=True)
class PassageCandidate:
    passage_id: str
    source_id: str
    text_version_id: str
    ordinal: int
    text: str
    word_count: int


@dataclass(frozen=True)
class SemanticHint:
    hint_id: str
    passage_id: str
    text: str
