"""Loading and validation for the versioned guided-question product catalog."""

import json
import re
from pathlib import Path

from ..models import GuidedQuestion, QuestionCatalog

_QUESTION_ID = re.compile(r"[a-z][a-z0-9_]*")
_ALLOWED_KINDS = {"question", "state"}


def load_question_catalog(path: Path) -> QuestionCatalog:
    """Loads stable guided prompts and rejects malformed/duplicate product IDs."""
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


def catalog_payload(catalog: QuestionCatalog) -> dict[str, object]:
    """Returns the deterministic JSON representation embedded in LLM curation bundles."""
    return {
        "schema_version": 1,
        "catalog_id": catalog.catalog_id,
        "language": catalog.language,
        "items": [
            {"id": item.id, "kind": item.kind, "theme": item.theme, "text": item.text}
            for item in catalog.items
        ],
    }
