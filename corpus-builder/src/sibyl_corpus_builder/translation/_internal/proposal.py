"""Import and revalidation of external large-LLM curated-passage translations.

The generated target text is intentionally preserved exactly as returned after
review; local validation proves source identity, completeness, provenance, and
stored translation hashes, but does not claim to judge literary translation quality.
"""

import json
from pathlib import Path

from sibyl_corpus_core.hashing import sha256_file, sha256_text
from sibyl_corpus_core.models import SourceDocument
from sibyl_corpus_core.prepared_sources import load_prepared_sources

from ..models import ValidatedMachineTranslation, ValidatedTranslatedPassage
from .source import resolve_translation_source, resolve_translation_source_from_documents
from .validation import (
    require_nonblank,
    validate_bundle_id,
    validate_id,
    validate_language,
    validate_sha256,
)


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _normalize_translation(
    *, source, raw: dict[str, object], input_label: str
) -> dict[str, object]:
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported translation schema_version in {input_label}")
    translation_id = validate_id(raw.get("translation_id"), "translation_id")
    source_bundle_id = validate_bundle_id(raw.get("source_bundle_id"))
    if source_bundle_id != source.bundle_id:
        raise ValueError("Translation source_bundle_id does not match current curated source input")
    source_curation_id = validate_id(raw.get("source_curation_id"), "source_curation_id")
    if source_curation_id != source.source_curation_id:
        raise ValueError("Translation source_curation_id does not match current curation")
    if raw.get("translation_method") != "large_llm":
        raise ValueError("Translation requires translation_method = 'large_llm'")
    target_language = validate_language(raw.get("target_language"))
    if target_language.casefold() != source.target_language.casefold():
        raise ValueError(
            "Translation target_language "
            f"{target_language!r} does not match {source.target_language!r}"
        )
    provider = require_nonblank(raw.get("translation_provider"), "translation_provider")
    model = require_nonblank(raw.get("translation_model"), "translation_model")
    prompt_version = require_nonblank(raw.get("prompt_version"), "prompt_version")

    source_by_id = {passage.passage_id: passage for passage in source.passages}
    raw_passages = raw.get("passages")
    if not isinstance(raw_passages, list) or not raw_passages:
        raise ValueError("Translation contains no passages")
    normalized_passages: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in raw_passages:
        if not isinstance(item, dict):
            raise ValueError("Translated passage must be an object")
        passage_id = str(item.get("passage_id", ""))
        if passage_id in seen:
            raise ValueError(f"Duplicate translated passage_id: {passage_id}")
        seen.add(passage_id)
        source_passage = source_by_id.get(passage_id)
        if source_passage is None:
            raise ValueError(f"Unknown curated passage_id in translation: {passage_id!r}")
        source_hash = validate_sha256(item.get("source_text_sha256"), "source_text")
        if source_hash != source_passage.source_text_sha256:
            raise ValueError(f"Translation source text SHA-256 mismatch for {passage_id}")
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Translation text must not be blank for {passage_id}")
        actual_translation_sha256 = sha256_text(text)
        declared_translation_sha256 = item.get("text_sha256")
        if declared_translation_sha256 is not None:
            translation_sha256 = validate_sha256(declared_translation_sha256, "translation text")
            if translation_sha256 != actual_translation_sha256:
                raise ValueError(f"Translation text SHA-256 mismatch for {passage_id}")
        normalized_passages.append(
            {
                "passage_id": passage_id,
                "work_id": source_passage.work_id,
                "source_text_version_id": source_passage.text_version_id,
                "source_text_sha256": source_passage.source_text_sha256,
                "text": text,
                "text_sha256": actual_translation_sha256,
            }
        )

    expected = set(source_by_id)
    missing = expected - seen
    if missing:
        raise ValueError(f"Translation is missing curated passage IDs: {sorted(missing)}")
    normalized_passages.sort(key=lambda item: str(item["passage_id"]))
    return {
        "schema_version": 1,
        "translation_id": translation_id,
        "source_bundle_id": source.bundle_id,
        "source_curation_id": source.source_curation_id,
        "translation_method": "large_llm",
        "target_language": source.target_language,
        "translation_provider": provider,
        "translation_model": model,
        "prompt_version": prompt_version,
        "passages": normalized_passages,
    }


def import_translation(
    *,
    source_dir: Path,
    questions_path: Path,
    curation_path: Path,
    target_language: str,
    input_path: Path,
    output_path: Path,
) -> Path:
    """Validates a complete LLM translation proposal and writes a local reproducible artifact."""
    source = resolve_translation_source(
        source_dir=source_dir,
        questions_path=questions_path,
        curation_path=curation_path,
        target_language=target_language,
    )
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Translation proposal root must be an object")
    normalized = _normalize_translation(source=source, raw=raw, input_label=str(input_path))
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_json_bytes(normalized))
    return output_path


def load_validated_translation_from_documents(
    *,
    documents: list[SourceDocument],
    questions_path: Path,
    curation_path: Path,
    translation_path: Path,
) -> ValidatedMachineTranslation:
    """Revalidates one generated translation artifact against current canonical curation input."""
    raw = json.loads(translation_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Validated translation root must be an object")
    target_language = validate_language(raw.get("target_language"))
    source = resolve_translation_source_from_documents(
        documents=documents,
        questions_path=questions_path,
        curation_path=curation_path,
        target_language=target_language,
    )
    normalized = _normalize_translation(source=source, raw=raw, input_label=str(translation_path))
    return ValidatedMachineTranslation(
        translation_id=str(normalized["translation_id"]),
        source_curation_id=str(normalized["source_curation_id"]),
        source_bundle_id=str(normalized["source_bundle_id"]),
        target_language=str(normalized["target_language"]),
        translation_provider=str(normalized["translation_provider"]),
        translation_model=str(normalized["translation_model"]),
        prompt_version=str(normalized["prompt_version"]),
        artifact_sha256=sha256_file(translation_path),
        passages=tuple(
            ValidatedTranslatedPassage(
                passage_id=str(item["passage_id"]),
                work_id=str(item["work_id"]),
                source_text_version_id=str(item["source_text_version_id"]),
                source_text_sha256=str(item["source_text_sha256"]),
                text=str(item["text"]),
                text_sha256=str(item["text_sha256"]),
            )
            for item in normalized["passages"]
        ),
    )


def load_validated_translation(
    *, source_dir: Path, questions_path: Path, curation_path: Path, translation_path: Path
) -> ValidatedMachineTranslation:
    """Loads one prepared source set and returns a fully revalidated translation artifact."""
    return load_validated_translation_from_documents(
        documents=load_prepared_sources(source_dir),
        questions_path=questions_path,
        curation_path=curation_path,
        translation_path=translation_path,
    )


def validate_translation(
    *, source_dir: Path, questions_path: Path, curation_path: Path, translation_path: Path
) -> None:
    """Revalidates a generated translation artifact without rewriting it."""
    load_validated_translation(
        source_dir=source_dir,
        questions_path=questions_path,
        curation_path=curation_path,
        translation_path=translation_path,
    )



def translation_source_curation_id(translation_path: Path) -> str:
    """Returns the curation ID required by one validated translation artifact."""
    raw = json.loads(translation_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported translation schema_version in {translation_path}")
    return validate_id(raw.get("source_curation_id"), "source_curation_id")

def translation_source_passage_ids(translation_path: Path) -> frozenset[str]:
    """Returns curated passage IDs required by one validated translation artifact."""
    raw = json.loads(translation_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported translation schema_version in {translation_path}")
    raw_passages = raw.get("passages")
    if not isinstance(raw_passages, list) or not raw_passages:
        raise ValueError("Translation contains no passages")
    ids: set[str] = set()
    for item in raw_passages:
        if not isinstance(item, dict):
            raise ValueError("Translated passage must be an object")
        passage_id = str(item.get("passage_id", ""))
        if not passage_id:
            raise ValueError("Translated passage requires passage_id")
        if passage_id in ids:
            raise ValueError(f"Duplicate translated passage_id: {passage_id}")
        ids.add(passage_id)
    return frozenset(ids)
