"""Import and revalidation of large-LLM curation metadata.

The external model chooses meaningful ranges and question relationships. This module never trusts
model-produced literary wording: it resolves every locator against local canonical sources,
verifies hashes, derives deterministic curated passage IDs, and writes only Git-safe metadata.
"""

import json
from pathlib import Path

from .questions import load_question_catalog
from .validation import (
    document_index,
    normalize_passage,
    validate_bundle_id,
    validate_proposal_id,
)


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def import_curation(
    *,
    source_dir: Path,
    questions_path: Path,
    input_path: Path,
    output_path: Path,
) -> Path:
    """Validates an LLM proposal and writes normalized locator/hash/question metadata."""
    catalog = load_question_catalog(questions_path)
    documents = document_index(source_dir)
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported curation proposal schema_version in {input_path}")
    proposal_id = validate_proposal_id(raw.get("proposal_id"))
    if raw.get("question_catalog_id") != catalog.catalog_id:
        raise ValueError(
            "Curation proposal question_catalog_id does not match the selected question catalog"
        )
    if raw.get("curation_method") != "large_llm":
        raise ValueError("Curation proposal requires curation_method = 'large_llm'")
    source_bundle_id = validate_bundle_id(raw.get("source_bundle_id"))
    raw_passages = raw.get("passages")
    if not isinstance(raw_passages, list) or not raw_passages:
        raise ValueError("Curation proposal contains no passages")

    normalized: list[dict[str, object]] = []
    seen_passages: set[tuple[str, str, str]] = set()
    for raw_passage in raw_passages:
        if not isinstance(raw_passage, dict):
            raise ValueError("Curation passage must be an object")
        passage = normalize_passage(
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
    """Revalidates Git-tracked curated metadata against the current prepared canonical sources."""
    catalog = load_question_catalog(questions_path)
    documents = document_index(source_dir)
    raw = json.loads(curation_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported curated curation schema_version in {curation_path}")
    validate_proposal_id(raw.get("curation_id"), label="curation_id")
    validate_bundle_id(raw.get("source_bundle_id"), label="source_bundle_id")
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
        normalized = normalize_passage(
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
