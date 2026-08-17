"""Automatic-build-only passage and semantic-hint models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PassageCandidate:
    """Exact canonical character range prepared by the automatic splitter for persistence."""

    passage_id: str
    source_id: str
    text_version_id: str
    ordinal: int
    text: str
    word_count: int
    source_start: int
    source_end: int
    source_locator: str


@dataclass(frozen=True)
class SemanticHint:
    """Internal retrieval text linked to one automatic passage and never exposed as quotation."""

    hint_id: str
    passage_id: str
    text: str
