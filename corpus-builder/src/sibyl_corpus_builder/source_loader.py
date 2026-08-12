import json
from pathlib import Path

from .models import SourceDocument


_ALLOWED_CATEGORIES = {"literature", "philosophy", "sacred_text"}
_ALLOWED_TEXT_ROLES = {"original", "human_translation", "machine_translation"}


def load_sources(source_dir: Path) -> list[SourceDocument]:
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

        text = text_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
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
