"""Runtime manifest assembly for automatic and guided corpus build output."""

import json
from pathlib import Path

from sibyl_corpus_core.models import SourceDocument

from ..config import BuilderConfig


def write_manifest(
    path: Path,
    *,
    config: BuilderConfig,
    documents: list[SourceDocument],
    passage_count: int,
    hint_count: int,
    guided_question_count: int = 0,
    guided_mapping_count: int = 0,
    machine_translation_count: int = 0,
) -> None:
    """Writes format/embedding compatibility metadata and guided diagnostics."""
    embedding_manifest: dict[str, object] = {
        "provider": config.embeddings.provider,
        "dimensions": config.embeddings.dimensions,
        "normalize": config.embeddings.normalize,
    }
    if config.embeddings.model_id:
        embedding_manifest["model_id"] = config.embeddings.model_id
    if config.embeddings.passage_prefix:
        embedding_manifest["passage_prefix"] = config.embeddings.passage_prefix
    if config.embeddings.query_prefix:
        embedding_manifest["query_prefix"] = config.embeddings.query_prefix

    manifest = {
        "format_version": config.format_version,
        "language": config.language,
        "embedding": embedding_manifest,
        "hints": {"provider": config.hints.provider},
        "content": {
            "target_language": config.language,
            "source_languages": sorted({document.language for document in documents}),
            "categories": sorted({document.category for document in documents}),
        },
        "counts": {
            "works": len(documents),
            "passages": passage_count,
            "hints": hint_count,
            "guided_questions": guided_question_count,
            "guided_mappings": guided_mapping_count,
            "machine_translations": machine_translation_count,
        },
        "artifacts": {"corpus": "corpus.db", "vectors": "vectors.json"},
    }
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
