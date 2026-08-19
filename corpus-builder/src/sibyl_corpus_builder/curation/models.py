"""Public data contracts for guided questions and validated literary curation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuidedQuestion:
    """One stable guided prompt that may map to many curated literary passages."""

    id: str
    kind: str
    theme: str
    text: str


@dataclass(frozen=True)
class QuestionCatalog:
    """Versioned guided-question catalog referenced by validated curation mappings."""

    catalog_id: str
    language: str
    items: tuple[GuidedQuestion, ...]

    @property
    def ids(self) -> frozenset[str]:
        """Returns the immutable set of IDs accepted by curation mappings."""
        return frozenset(item.id for item in self.items)


@dataclass(frozen=True)
class CuratedQuestionMatch:
    """One validated guided-question relationship and its normalized curation strength."""

    question_id: str
    strength: float


@dataclass(frozen=True)
class ValidatedCuratedPassage:
    """One exact canonical passage revalidated for safe runtime-corpus materialization."""

    passage_id: str
    work_id: str
    text_version_id: str
    source_locator: str
    canonical_sha256: str
    text_sha256: str
    text: str
    word_count: int
    matches: tuple[CuratedQuestionMatch, ...]


@dataclass(frozen=True)
class ValidatedCuration:
    """One normalized curation file after exact-text, hash, and question-link validation."""

    curation_id: str
    question_catalog_id: str
    passages: tuple[ValidatedCuratedPassage, ...]
