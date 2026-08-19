"""Resolve exact curated source passages used as machine-translation input.

The translation feature never accepts arbitrary LLM source wording. It reuses the
public curation trust boundary, then adds source-language/target-language checks
and a deterministic bundle identity over the exact curated passage hashes.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from sibyl_corpus_builder.curation import load_validated_curation_from_documents
from sibyl_corpus_core.models import SourceDocument
from sibyl_corpus_core.prepared_sources import load_prepared_sources

from .validation import validate_language


@dataclass(frozen=True)
class TranslationSourcePassage:
    """Exact curated source passage plus language metadata for translation."""

    passage_id: str
    work_id: str
    text_version_id: str
    source_language: str
    source_text_sha256: str
    rights_status: str | None
    text: str


@dataclass(frozen=True)
class TranslationSource:
    """Deterministic translation input resolved from one validated curation."""

    bundle_id: str
    source_curation_id: str
    target_language: str
    passages: tuple[TranslationSourcePassage, ...]


def resolve_translation_source_from_documents(
    *,
    documents: list[SourceDocument],
    questions_path: Path,
    curation_path: Path,
    target_language: str,
) -> TranslationSource:
    """Revalidates curated passages and selects those whose source language differs from target."""
    target_language = validate_language(target_language)
    document_map = {
        (document.source_id, document.text_version_id): document for document in documents
    }
    validated = load_validated_curation_from_documents(
        documents=documents,
        questions_path=questions_path,
        curation_path=curation_path,
    )

    passages: list[TranslationSourcePassage] = []
    for passage in validated.passages:
        document = document_map[(passage.work_id, passage.text_version_id)]
        if document.language.casefold() == target_language.casefold():
            continue
        if document.text_role != "original":
            raise ValueError(
                "Curated machine translation currently requires original source text; "
                f"got {document.text_role!r} for {passage.work_id}/{passage.text_version_id}"
            )
        passages.append(
            TranslationSourcePassage(
                passage_id=passage.passage_id,
                work_id=passage.work_id,
                text_version_id=passage.text_version_id,
                source_language=document.language,
                source_text_sha256=passage.text_sha256,
                rights_status=document.rights_status,
                text=passage.text,
            )
        )
    if not passages:
        raise ValueError(
            f"Curation {curation_path} has no passages requiring translation to {target_language}"
        )

    passages.sort(key=lambda item: (item.work_id, item.text_version_id, item.passage_id))
    identity_payload = {
        "source_curation_id": validated.curation_id,
        "target_language": target_language,
        "passages": [
            {
                "passage_id": item.passage_id,
                "work_id": item.work_id,
                "text_version_id": item.text_version_id,
                "source_text_sha256": item.source_text_sha256,
            }
            for item in passages
        ],
    }
    identity = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
    bundle_id = f"tb_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"
    return TranslationSource(
        bundle_id=bundle_id,
        source_curation_id=validated.curation_id,
        target_language=target_language,
        passages=tuple(passages),
    )


def resolve_translation_source(
    *, source_dir: Path, questions_path: Path, curation_path: Path, target_language: str
) -> TranslationSource:
    """Loads one prepared source set and resolves deterministic curated translation input."""
    return resolve_translation_source_from_documents(
        documents=load_prepared_sources(source_dir),
        questions_path=questions_path,
        curation_path=curation_path,
        target_language=target_language,
    )
