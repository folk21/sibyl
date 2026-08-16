from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .models import SourceDocument
from .source_loader import load_sources
from .splitter import word_count

_QUESTION_ID = re.compile(r"[a-z][a-z0-9_]*")
_PROPOSAL_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")
_LOCATOR = re.compile(r"chars:(\d+):(\d+)")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_BUNDLE_ID = re.compile(r"cb_[0-9a-f]{20}")
_ALLOWED_KINDS = {"question", "state"}
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


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
        return frozenset(item.id for item in self.items)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load_question_catalog(path: Path) -> QuestionCatalog:
    """Loads and validates the versioned guided-question product catalog."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported question catalog schema_version in {path}")
    catalog_id = str(raw.get("catalog_id", "")).strip()
    language = str(raw.get("language", "")).strip()
    if not catalog_id or not language:
        raise ValueError("Question catalog requires catalog_id and language")

    items: list[GuidedQuestion] = []
    seen_ids: set[str] = set()
    for item in raw.get("items", []):
        item_id = str(item.get("id", ""))
        if not _QUESTION_ID.fullmatch(item_id):
            raise ValueError(f"Invalid guided question id: {item_id!r}")
        if item_id in seen_ids:
            raise ValueError(f"Duplicate guided question id: {item_id}")
        seen_ids.add(item_id)
        kind = str(item.get("kind", ""))
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"Invalid guided question kind for {item_id}: {kind!r}")
        theme = str(item.get("theme", "")).strip()
        text = str(item.get("text", "")).strip()
        if not theme or not text:
            raise ValueError(f"Guided question {item_id} requires theme and text")
        items.append(GuidedQuestion(id=item_id, kind=kind, theme=theme, text=text))
    if not items:
        raise ValueError("Question catalog contains no items")
    return QuestionCatalog(catalog_id=catalog_id, language=language, items=tuple(items))


def _catalog_payload(catalog: QuestionCatalog) -> dict[str, object]:
    return {
        "schema_version": 1,
        "catalog_id": catalog.catalog_id,
        "language": catalog.language,
        "items": [
            {"id": item.id, "kind": item.kind, "theme": item.theme, "text": item.text}
            for item in catalog.items
        ],
    }


def _verified_document_hash(document: SourceDocument) -> str:
    actual = _sha256_text(document.text)
    declared = document.canonical_text_sha256
    if declared is not None and declared.lower() != actual:
        raise ValueError(
            "Prepared source canonical SHA-256 mismatch for "
            f"{document.source_id}/{document.text_version_id}: declared {declared}, actual {actual}"
        )
    return actual


def _zip_write(archive: ZipFile, name: str, data: bytes) -> None:
    info = ZipInfo(name, date_time=_FIXED_ZIP_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def export_curation_bundle(
    *,
    source_dir: Path,
    questions_path: Path,
    output_path: Path,
    work_ids: list[str] | None = None,
    allow_unapproved: bool = False,
) -> Path:
    """Exports canonical texts and guided questions as a deterministic local LLM input bundle."""
    catalog = load_question_catalog(questions_path)
    documents = load_sources(source_dir)
    selected_ids = set(work_ids or [])
    if selected_ids:
        known_ids = {document.source_id for document in documents}
        unknown = selected_ids - known_ids
        if unknown:
            raise ValueError(f"Unknown prepared work IDs for curation export: {sorted(unknown)}")
        documents = [document for document in documents if document.source_id in selected_ids]
    if not documents:
        raise ValueError("Curation export contains no prepared works")
    if not allow_unapproved:
        unapproved = [
            f"{document.source_id}/{document.text_version_id}"
            for document in documents
            if document.rights_status != "approved"
        ]
        if unapproved:
            raise ValueError(
                "Curation export includes source versions without approved rights metadata: "
                f"{unapproved}. Use --allow-unapproved only after separately confirming that "
                "the concrete texts may be sent to the external curation service."
            )

    catalog_bytes = _json_bytes(_catalog_payload(catalog))
    work_entries: list[dict[str, object]] = []
    work_files: list[tuple[str, bytes]] = []
    seen_versions: set[tuple[str, str]] = set()
    for index, document in enumerate(
        sorted(documents, key=lambda value: (value.source_id, value.text_version_id))
    ):
        key = (document.source_id, document.text_version_id)
        if key in seen_versions:
            raise ValueError(f"Duplicate prepared text version: {key[0]}/{key[1]}")
        seen_versions.add(key)
        canonical_sha256 = _verified_document_hash(document)
        file_name = f"works/{index + 1:04d}.txt"
        text_bytes = document.text.encode("utf-8")
        work_files.append((file_name, text_bytes))
        work_entries.append(
            {
                "work_id": document.source_id,
                "text_version_id": document.text_version_id,
                "author": document.author,
                "title": document.work,
                "language": document.language,
                "original_language": document.original_language,
                "category": document.category,
                "text_role": document.text_role,
                "rights_status": document.rights_status,
                "canonical_sha256": canonical_sha256,
                "character_count": len(document.text),
                "utf8_bytes": len(text_bytes),
                "file": file_name,
            }
        )

    identity_payload = {
        "question_catalog_sha256": _sha256_bytes(catalog_bytes),
        "works": [
            {
                "work_id": entry["work_id"],
                "text_version_id": entry["text_version_id"],
                "canonical_sha256": entry["canonical_sha256"],
            }
            for entry in work_entries
        ],
    }
    identity = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
    bundle_id = f"cb_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"
    manifest = {
        "schema_version": 1,
        "bundle_id": bundle_id,
        "purpose": "llm_passage_curation",
        "question_catalog": {
            "catalog_id": catalog.catalog_id,
            "language": catalog.language,
            "file": "questions.json",
            "sha256": _sha256_bytes(catalog_bytes),
        },
        "works": work_entries,
    }

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = output_path.with_name(f".{output_path.name}.staging")
    if staging.exists():
        staging.unlink()
    try:
        with ZipFile(staging, "w") as archive:
            _zip_write(archive, "manifest.json", _json_bytes(manifest))
            _zip_write(archive, "questions.json", catalog_bytes)
            for file_name, data in work_files:
                _zip_write(archive, file_name, data)
        if output_path.exists():
            output_path.unlink()
        staging.replace(output_path)
    except BaseException:
        if staging.exists():
            staging.unlink()
        raise
    return output_path


def _document_index(source_dir: Path) -> dict[tuple[str, str], tuple[SourceDocument, str]]:
    documents = load_sources(source_dir)
    index: dict[tuple[str, str], tuple[SourceDocument, str]] = {}
    for document in documents:
        key = (document.source_id, document.text_version_id)
        if key in index:
            raise ValueError(f"Duplicate prepared text version: {key[0]}/{key[1]}")
        index[key] = (document, _verified_document_hash(document))
    return index


def _parse_locator(value: object) -> tuple[str, int, int]:
    locator = str(value)
    match = _LOCATOR.fullmatch(locator)
    if match is None:
        raise ValueError(f"Invalid curation source locator: {locator!r}")
    start = int(match.group(1))
    end = int(match.group(2))
    if start >= end:
        raise ValueError(f"Curation source locator must have start < end: {locator}")
    return locator, start, end


def _validate_sha256(value: object, label: str) -> str:
    digest = str(value).lower()
    if not _SHA256.fullmatch(digest):
        raise ValueError(f"Invalid {label} SHA-256: {value!r}")
    return digest


def _normalize_matches(
    raw_matches: object, question_ids: frozenset[str]
) -> list[dict[str, object]]:
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


def _normalize_passage(
    raw: dict[str, object],
    *,
    documents: dict[tuple[str, str], tuple[SourceDocument, str]],
    question_ids: frozenset[str],
) -> dict[str, object]:
    work_id = str(raw.get("work_id", ""))
    text_version_id = str(raw.get("text_version_id", ""))
    key = (work_id, text_version_id)
    resolved = documents.get(key)
    if resolved is None:
        raise ValueError(f"Unknown prepared text version in curation: {work_id}/{text_version_id}")
    document, actual_canonical_sha256 = resolved

    canonical_sha256 = _validate_sha256(raw.get("canonical_sha256"), "canonical")
    if canonical_sha256 != actual_canonical_sha256:
        raise ValueError(
            "Curation canonical SHA-256 does not match prepared source for "
            f"{work_id}/{text_version_id}"
        )

    locator, start, end = _parse_locator(raw.get("source_locator"))
    if end > len(document.text):
        raise ValueError(
            f"Curation source locator is outside canonical text for {work_id}/{text_version_id}: "
            f"{locator} > {len(document.text)} characters"
        )
    selected_text = document.text[start:end]
    if not selected_text.strip():
        raise ValueError(f"Curated passage resolves to blank text: {work_id}/{locator}")
    text_sha256 = _validate_sha256(raw.get("text_sha256"), "text")
    actual_text_sha256 = _sha256_text(selected_text)
    if text_sha256 != actual_text_sha256:
        raise ValueError(f"Curation text SHA-256 mismatch for {work_id}/{locator}")

    matches = _normalize_matches(raw.get("matches"), question_ids)
    identity = f"{work_id}:{text_version_id}:{start}:{end}:{text_sha256}"
    passage_id = f"cp_{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]}"
    return {
        "passage_id": passage_id,
        "work_id": work_id,
        "text_version_id": text_version_id,
        "canonical_sha256": canonical_sha256,
        "source_locator": locator,
        "text_sha256": text_sha256,
        "word_count": word_count(selected_text),
        "matches": matches,
    }


def import_curation(
    *,
    source_dir: Path,
    questions_path: Path,
    input_path: Path,
    output_path: Path,
) -> Path:
    """Validates an LLM proposal against canonical text and writes normalized Git-safe metadata."""
    catalog = load_question_catalog(questions_path)
    documents = _document_index(source_dir)
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported curation proposal schema_version in {input_path}")
    proposal_id = str(raw.get("proposal_id", ""))
    if not _PROPOSAL_ID.fullmatch(proposal_id):
        raise ValueError(f"Invalid curation proposal_id: {proposal_id!r}")
    if raw.get("question_catalog_id") != catalog.catalog_id:
        raise ValueError(
            "Curation proposal question_catalog_id does not match the selected question catalog"
        )
    if raw.get("curation_method") != "large_llm":
        raise ValueError("Curation proposal requires curation_method = 'large_llm'")
    source_bundle_id = str(raw.get("source_bundle_id", ""))
    if not _BUNDLE_ID.fullmatch(source_bundle_id):
        raise ValueError(f"Invalid curation source_bundle_id: {source_bundle_id!r}")
    raw_passages = raw.get("passages")
    if not isinstance(raw_passages, list) or not raw_passages:
        raise ValueError("Curation proposal contains no passages")

    normalized: list[dict[str, object]] = []
    seen_passages: set[tuple[str, str, str]] = set()
    for raw_passage in raw_passages:
        if not isinstance(raw_passage, dict):
            raise ValueError("Curation passage must be an object")
        passage = _normalize_passage(
            raw_passage, documents=documents, question_ids=catalog.ids
        )
        key = (
            str(passage["work_id"]),
            str(passage["text_version_id"]),
            str(passage["source_locator"]),
        )
        if key in seen_passages:
            raise ValueError(
                "Duplicate curated passage locator; combine question matches into one "
                f"passage entry: {key[0]}/{key[2]}"
            )
        seen_passages.add(key)
        normalized.append(passage)

    normalized.sort(
        key=lambda value: (
            str(value["work_id"]),
            str(value["text_version_id"]),
            int(str(value["source_locator"]).split(":")[1]),
        )
    )
    output = {
        "schema_version": 1,
        "curation_id": proposal_id,
        "question_catalog_id": catalog.catalog_id,
        "curation_method": "large_llm",
        "source_bundle_id": source_bundle_id,
        "passages": normalized,
    }

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(_json_bytes(output))
    return output_path


def validate_curated_curation(
    *, source_dir: Path, questions_path: Path, curation_path: Path
) -> None:
    """Revalidates normalized curated mappings against current prepared canonical sources."""
    catalog = load_question_catalog(questions_path)
    documents = _document_index(source_dir)
    raw = json.loads(curation_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported curated curation schema_version in {curation_path}")
    curation_id = str(raw.get("curation_id", ""))
    if not _PROPOSAL_ID.fullmatch(curation_id):
        raise ValueError(f"Invalid curated curation_id: {curation_id!r}")
    source_bundle_id = str(raw.get("source_bundle_id", ""))
    if not _BUNDLE_ID.fullmatch(source_bundle_id):
        raise ValueError(f"Invalid curated source_bundle_id: {source_bundle_id!r}")
    if raw.get("question_catalog_id") != catalog.catalog_id:
        raise ValueError("Curated mapping question_catalog_id does not match question catalog")
    if raw.get("curation_method") != "large_llm":
        raise ValueError("Curated mapping requires curation_method = 'large_llm'")
    raw_passages = raw.get("passages")
    if not isinstance(raw_passages, list) or not raw_passages:
        raise ValueError("Curated mapping contains no passages")

    seen_ids: set[str] = set()
    for raw_passage in raw_passages:
        if not isinstance(raw_passage, dict):
            raise ValueError("Curated passage must be an object")
        normalized = _normalize_passage(
            raw_passage, documents=documents, question_ids=catalog.ids
        )
        passage_id = str(raw_passage.get("passage_id", ""))
        if passage_id != normalized["passage_id"]:
            raise ValueError(
                "Curated passage_id mismatch: "
                f"expected {normalized['passage_id']}, got {passage_id}"
            )
        if raw_passage.get("word_count") != normalized["word_count"]:
            raise ValueError(f"Curated word_count mismatch for {passage_id}")
        if passage_id in seen_ids:
            raise ValueError(f"Duplicate curated passage_id: {passage_id}")
        seen_ids.add(passage_id)
