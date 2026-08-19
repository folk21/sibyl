"""Exact-text validation primitives for LLM curation proposals and persisted mappings.

The LLM is allowed to make literary/semantic decisions, but this module is the trust boundary for
text integrity. Every proposed locator is resolved against a prepared canonical text version and
its SHA-256; the LLM output itself is never accepted as authoritative quotation text.
"""

import hashlib
import re
from pathlib import Path

from sibyl_corpus_core.hashing import sha256_text
from sibyl_corpus_core.locators import parse_character_locator
from sibyl_corpus_core.models import SourceDocument
from sibyl_corpus_core.text import word_count

_PROPOSAL_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")
_BUNDLE_ID = re.compile(r"cb_[0-9a-f]{20}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def validate_proposal_id(value: object, label: str = "proposal_id") -> str:
    """Validates stable proposal/curation IDs used in Git-tracked metadata."""
    result = str(value)
    if not _PROPOSAL_ID.fullmatch(result):
        raise ValueError(f"Invalid curation {label}: {result!r}")
    return result


def validate_bundle_id(value: object, label: str = "source_bundle_id") -> str:
    """Validates deterministic curation bundle identities."""
    result = str(value)
    if not _BUNDLE_ID.fullmatch(result):
        raise ValueError(f"Invalid curation {label}: {result!r}")
    return result


def validate_sha256(value: object, label: str) -> str:
    """Normalizes and validates one lowercase SHA-256 field."""
    digest = str(value).lower()
    if not _SHA256.fullmatch(digest):
        raise ValueError(f"Invalid {label} SHA-256: {value!r}")
    return digest


def verified_document_hash(document: SourceDocument) -> str:
    """Checks an optional prepared-source hash against exact canonical UTF-8 text."""
    actual = sha256_text(document.text)
    declared = document.canonical_text_sha256
    if declared is not None and declared.lower() != actual:
        raise ValueError(
            "Prepared source canonical SHA-256 mismatch for "
            f"{document.source_id}/{document.text_version_id}: declared {declared}, actual {actual}"
        )
    return actual


def document_index(
    documents: list[SourceDocument],
) -> dict[tuple[str, str], tuple[SourceDocument, str]]:
    """Indexes prepared text versions and pins each to its verified canonical hash."""
    index: dict[tuple[str, str], tuple[SourceDocument, str]] = {}
    for document in documents:
        key = (document.source_id, document.text_version_id)
        if key in index:
            raise ValueError(f"Duplicate prepared text version: {key[0]}/{key[1]}")
        index[key] = (document, verified_document_hash(document))
    return index


def normalize_matches(
    raw_matches: object, question_ids: frozenset[str]
) -> list[dict[str, object]]:
    """Validates unique question links and normalized 0..1 curation strengths."""
    if not isinstance(raw_matches, list) or not raw_matches:
        raise ValueError("Curated passage requires at least one question match")
    matches: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in raw_matches:
        if not isinstance(raw, dict):
            raise ValueError("Question match must be an object")
        question_id = str(raw.get("question_id", ""))
        if question_id not in question_ids:
            raise ValueError(f"Unknown guided question id in curation: {question_id!r}")
        if question_id in seen:
            raise ValueError(f"Duplicate question match in one curated passage: {question_id}")
        seen.add(question_id)
        strength_raw = raw.get("strength")
        if isinstance(strength_raw, bool) or not isinstance(strength_raw, (int, float)):
            raise ValueError(f"Curation strength for {question_id} must be numeric")
        strength = float(strength_raw)
        if not 0.0 <= strength <= 1.0:
            raise ValueError(f"Curation strength for {question_id} must be between 0 and 1")
        matches.append({"question_id": question_id, "strength": strength})
    return sorted(matches, key=lambda value: str(value["question_id"]))


def normalize_passage(
    raw: dict[str, object],
    *,
    documents: dict[tuple[str, str], tuple[SourceDocument, str]],
    question_ids: frozenset[str],
) -> dict[str, object]:
    """Resolves one LLM-proposed locator and returns deterministic Git-safe metadata."""
    work_id = str(raw.get("work_id", ""))
    text_version_id = str(raw.get("text_version_id", ""))
    key = (work_id, text_version_id)
    resolved = documents.get(key)
    if resolved is None:
        raise ValueError(f"Unknown prepared text version in curation: {work_id}/{text_version_id}")
    document, actual_canonical_sha256 = resolved

    canonical_sha256 = validate_sha256(raw.get("canonical_sha256"), "canonical")
    if canonical_sha256 != actual_canonical_sha256:
        raise ValueError(
            "Curation canonical SHA-256 does not match prepared source for "
            f"{work_id}/{text_version_id}"
        )

    character_range = parse_character_locator(raw.get("source_locator"))
    try:
        selected_text = character_range.extract(document.text)
    except ValueError as error:
        raise ValueError(
            f"Curation source locator is outside canonical text for {work_id}/{text_version_id}: "
            f"{character_range.locator}"
        ) from error
    if not selected_text.strip():
        raise ValueError(
            "Curated passage resolves to blank text: "
            f"{work_id}/{character_range.locator}"
        )

    text_sha256 = validate_sha256(raw.get("text_sha256"), "text")
    actual_text_sha256 = sha256_text(selected_text)
    if text_sha256 != actual_text_sha256:
        raise ValueError(f"Curation text SHA-256 mismatch for {work_id}/{character_range.locator}")

    matches = normalize_matches(raw.get("matches"), question_ids)
    identity = (
        f"{work_id}:{text_version_id}:{character_range.start}:{character_range.end}:{text_sha256}"
    )
    passage_id = f"cp_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"
    return {
        "passage_id": passage_id,
        "work_id": work_id,
        "text_version_id": text_version_id,
        "canonical_sha256": canonical_sha256,
        "source_locator": character_range.locator,
        "text_sha256": text_sha256,
        "word_count": word_count(selected_text),
        "matches": matches,
    }
