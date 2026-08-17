"""Deterministic export of prepared canonical texts for external large-LLM curation.

Pipeline position:

    prepared canonical sources + stable questions
                    -> THIS MODULE
                    -> local ZIP curation bundle
                    -> external large LLM
                    -> proposal import/validation

The bundle is intentionally not Git-tracked corpus data: it contains full canonical literary
texts. Export is deterministic so a repeated run over identical inputs produces identical bytes.
"""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from sibyl_corpus_core.hashing import sha256_bytes
from sibyl_corpus_core.prepared_sources import load_prepared_sources

from .questions import catalog_payload, load_question_catalog
from .validation import verified_document_hash

_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


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
    """Exports exact canonical texts/questions after explicit rights and identity checks."""
    catalog = load_question_catalog(questions_path)
    documents = load_prepared_sources(source_dir)
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

    catalog_bytes = _json_bytes(catalog_payload(catalog))
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
        canonical_sha256 = verified_document_hash(document)
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
        "question_catalog_sha256": sha256_bytes(catalog_bytes),
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
            "sha256": sha256_bytes(catalog_bytes),
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
