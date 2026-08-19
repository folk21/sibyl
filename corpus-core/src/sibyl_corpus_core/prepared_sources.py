"""Loads deterministic canonical source sets produced by source preparation.

Pipeline position:

    discover/acquire/normalize/prepare -> prepared ``manifest.json`` + canonical text files
                                      -> THIS MODULE
                                      -> automatic build and LLM curation

This module owns only the shared read/composition boundary. It does not acquire sources, split
passages, generate embeddings, or interpret LLM curation metadata.
"""

import json
from collections.abc import Iterable
from pathlib import Path

from .models import SourceDocument
from .text import normalize_newlines

_ALLOWED_CATEGORIES = {"literature", "philosophy", "sacred_text"}
_ALLOWED_TEXT_ROLES = {"original", "human_translation", "machine_translation"}


def load_prepared_sources(source_dir: Path) -> list[SourceDocument]:
    """Loads one prepared canonical source set while validating shared controlled fields."""
    manifest_path = source_dir / "manifest.json"
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))["works"]
    documents: list[SourceDocument] = []

    for entry in entries:
        text_path = source_dir / entry["file"]
        language = entry.get("language", "en")
        category = entry.get("category", "literature")
        text_role = entry.get("text_role", "original")
        if category not in _ALLOWED_CATEGORIES:
            raise ValueError(f"Unsupported work category: {category}")
        if text_role not in _ALLOWED_TEXT_ROLES:
            raise ValueError(f"Unsupported text role: {text_role}")

        text = normalize_newlines(text_path.read_text(encoding="utf-8"))
        documents.append(
            SourceDocument(
                source_id=entry["id"],
                text_version_id=entry.get("text_version_id", f'{entry["id"]}:source'),
                author=entry["author"],
                work=entry["title"],
                text=text,
                source_name=entry.get("source_name", entry["file"]),
                language=language,
                original_language=entry.get("original_language", language),
                category=category,
                text_role=text_role,
                translator=entry.get("translator"),
                translation_provider=entry.get("translation_provider"),
                translation_model=entry.get("translation_model"),
                source_uri=entry.get("source_uri"),
                source_locator=entry.get("source_locator"),
                source_artifact_sha256=entry.get("source_artifact_sha256"),
                canonical_text_sha256=entry.get("canonical_text_sha256"),
                rights_status=entry.get("rights_status"),
                rights_jurisdiction=entry.get("rights_jurisdiction"),
                provenance=entry.get("provenance", entry.get("source_name", entry["file"])),
            )
        )
    return documents


def load_prepared_source_sets(source_dirs: Iterable[Path]) -> list[SourceDocument]:
    """Composes prepared sets and rejects ambiguous duplicate text/work identities.

    Input directories remain independent preparation artifacts. Composition is deterministic and
    in-memory so corpus assembly does not need a copied/hand-merged prepared directory.
    """
    resolved_dirs = [Path(source_dir) for source_dir in source_dirs]
    if not resolved_dirs:
        raise ValueError("At least one prepared source directory is required")

    documents: list[SourceDocument] = []
    seen_versions: set[tuple[str, str]] = set()
    work_identity: dict[str, tuple[str, str, str, str]] = {}
    for source_dir in resolved_dirs:
        for document in load_prepared_sources(source_dir):
            version_key = (document.source_id, document.text_version_id)
            if version_key in seen_versions:
                raise ValueError(
                    "Duplicate prepared text version across source sets: "
                    f"{document.source_id}/{document.text_version_id}"
                )
            seen_versions.add(version_key)

            identity = (
                document.author,
                document.work,
                document.original_language,
                document.category,
            )
            previous = work_identity.get(document.source_id)
            if previous is not None and previous != identity:
                raise ValueError(
                    "Conflicting prepared work identity across source sets: "
                    f"{document.source_id}"
                )
            work_identity[document.source_id] = identity
            documents.append(document)

    return documents
