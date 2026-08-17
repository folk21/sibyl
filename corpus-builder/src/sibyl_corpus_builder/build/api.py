"""Public API for automatic passage preparation and runtime corpus publication.

Pipeline position:

    prepared canonical sources
        -> automatic natural-boundary splitting
        -> semantic hints
        -> embeddings (with resumable cache)
        -> corpus.db + vectors.json + manifest.json
        -> validation
        -> atomic publication

This is the mechanical/open-ended retrieval path kept for arbitrary user questions. It remains
separate from LLM curation, which selects its own meaningful canonical ranges for guided prompts.
"""

import json
from pathlib import Path

from sibyl_corpus_core.atomic import staging_directory
from sibyl_corpus_core.prepared_sources import load_prepared_sources

from .config import BuilderConfig, load_config
from ._internal.database import create_database
from ._internal.embedding_pipeline import resolve_embeddings
from ._internal.hints import DeterministicHintGenerator, PassageTextHintGenerator
from ._internal.manifest import write_manifest
from ._internal.runtime_model import download_runtime_model
from ._internal.splitter import split_document
from ._internal.validation import validate_corpus


def _hint_generator(config: BuilderConfig):
    if config.hints.provider == "deterministic":
        return DeterministicHintGenerator()
    if config.hints.provider == "passage_text":
        return PassageTextHintGenerator()
    raise ValueError(f"Unsupported hint provider: {config.hints.provider}")


def inspect_passages(config_path: Path, source_dir: Path, output: Path) -> None:
    """Writes automatic exact passage candidates as JSONL for developer inspection."""
    config = load_config(config_path)
    records: list[dict[str, object]] = []
    for document in load_prepared_sources(source_dir):
        for passage in split_document(document, config.passages):
            records.append(
                {
                    "passage_id": passage.passage_id,
                    "work_id": passage.source_id,
                    "text_version_id": passage.text_version_id,
                    "ordinal": passage.ordinal,
                    "source_locator": passage.source_locator,
                    "word_count": passage.word_count,
                    "text": passage.text,
                }
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} passage candidates to {output}")


def build_corpus(config: BuilderConfig, source_dir: Path, output_dir: Path) -> None:
    """Builds, validates, and atomically publishes automatic runtime corpus artifacts."""
    print("[1/5] Loading sources and extracting passages...", flush=True)
    documents = load_prepared_sources(source_dir)
    passages = [
        passage
        for document in documents
        for passage in split_document(document, config.passages)
    ]

    hint_generator = _hint_generator(config)
    hints = [
        hint
        for passage in passages
        for hint in hint_generator.generate(passage, config.hints.hints_per_passage)
    ]

    print(
        f"Prepared {len(documents)} works, {len(passages)} passages, {len(hints)} embedding hints.",
        flush=True,
    )
    print("[2/5] Resolving embeddings...", flush=True)
    vectors = resolve_embeddings(config, hints, source_dir.resolve())

    output_dir = output_dir.resolve()
    with staging_directory(output_dir) as staging_dir:
        print("[3/5] Writing corpus artifacts...", flush=True)
        corpus_path = staging_dir / "corpus.db"
        create_database(
            corpus_path,
            format_version=config.format_version,
            language=config.language,
            embedding_provider=config.embeddings.provider,
            embedding_model=config.embeddings.model_id,
            embedding_dimensions=config.embeddings.dimensions,
            documents=documents,
            passages=passages,
            hints=hints,
        )
        (staging_dir / "vectors.json").write_text(
            json.dumps(vectors, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        write_manifest(
            staging_dir / "manifest.json",
            config=config,
            documents=documents,
            passage_count=len(passages),
            hint_count=len(hints),
        )

        print("[4/5] Validating corpus...", flush=True)
        validate_corpus(corpus_path)
        print("[5/5] Publishing corpus...", flush=True)

    print(f"Published corpus: {output_dir}", flush=True)


__all__ = [
    "build_corpus",
    "download_runtime_model",
    "inspect_passages",
    "load_config",
    "validate_corpus",
]
