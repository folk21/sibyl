"""Public data contracts for the stable guided-question catalog."""

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
    """Versioned guided-question catalog referenced by LLM curation mappings."""

    catalog_id: str
    language: str
    items: tuple[GuidedQuestion, ...]

    @property
    def ids(self) -> frozenset[str]:
        """Returns the immutable set of IDs accepted by curation mappings."""
        return frozenset(item.id for item in self.items)
