"""Public data contracts for validated build-time machine translations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidatedTranslatedPassage:
    """One generated stored translation pinned to an exact curated source passage."""

    passage_id: str
    work_id: str
    source_text_version_id: str
    source_text_sha256: str
    text: str
    text_sha256: str


@dataclass(frozen=True)
class ValidatedMachineTranslation:
    """One locally validated machine-translation artifact ready for corpus assembly."""

    translation_id: str
    source_curation_id: str
    source_bundle_id: str
    target_language: str
    translation_provider: str
    translation_model: str
    prompt_version: str
    artifact_sha256: str
    passages: tuple[ValidatedTranslatedPassage, ...]
