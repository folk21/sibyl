"""Deterministic ZIP export of exact curated passages for external LLM translation."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from .source import resolve_translation_source

_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _zip_write(archive: ZipFile, name: str, data: bytes) -> None:
    info = ZipInfo(name, date_time=_FIXED_ZIP_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def export_translation_bundle(
    *,
    source_dir: Path,
    questions_path: Path,
    curation_path: Path,
    target_language: str,
    output_path: Path,
    allow_unapproved: bool = False,
) -> Path:
    """Exports exact curated source text and deterministic identities for an explicit LLM step."""
    source = resolve_translation_source(
        source_dir=source_dir,
        questions_path=questions_path,
        curation_path=curation_path,
        target_language=target_language,
    )
    if not allow_unapproved:
        unapproved = [
            f"{passage.work_id}/{passage.text_version_id}"
            for passage in source.passages
            if passage.rights_status != "approved"
        ]
        if unapproved:
            raise ValueError(
                "Translation export includes source versions without approved rights metadata: "
                f"{sorted(set(unapproved))}. Use --allow-unapproved only after separately "
                "confirming that the concrete text may be sent to the external translation service."
            )

    manifest = {
        "schema_version": 1,
        "bundle_id": source.bundle_id,
        "purpose": "curated_passage_machine_translation",
        "source_curation_id": source.source_curation_id,
        "target_language": source.target_language,
        "passage_count": len(source.passages),
        "passages_file": "passages.json",
    }
    passages = {
        "schema_version": 1,
        "bundle_id": source.bundle_id,
        "target_language": source.target_language,
        "passages": [
            {
                "passage_id": passage.passage_id,
                "work_id": passage.work_id,
                "text_version_id": passage.text_version_id,
                "source_language": passage.source_language,
                "source_text_sha256": passage.source_text_sha256,
                "rights_status": passage.rights_status,
                "text": passage.text,
            }
            for passage in source.passages
        ],
    }

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = output_path.with_name(f".{output_path.name}.staging")
    if staging.exists():
        staging.unlink()
    try:
        with ZipFile(staging, "w") as archive:
            _zip_write(archive, "manifest.json", _json_bytes(manifest))
            _zip_write(archive, "passages.json", _json_bytes(passages))
        if output_path.exists():
            output_path.unlink()
        staging.replace(output_path)
    except BaseException:
        if staging.exists():
            staging.unlink()
        raise
    return output_path
