"""Public API for automatic passage preparation and runtime corpus publication.

Pipeline position:

    prepared canonical sources
        -> automatic natural-boundary splitting
        -> semantic hints
        -> embeddings (with resumable cache)
        + optional validated guided curation
        -> corpus.db + vectors.json + manifest.json
        -> validation
        -> atomic publication

The automatic path remains the mechanical/open-ended retrieval path for arbitrary user questions.
Optional guided curation is revalidated through the public curation boundary and materialized as
exact stored passages plus question mappings in the same runtime corpus.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from sibyl_corpus_core.atomic import staging_directory
from sibyl_corpus_core.models import SourceDocument
from sibyl_corpus_core.prepared_sources import load_prepared_source_sets, load_prepared_sources

from ..curation import load_question_catalog, load_validated_curation_from_documents
from ..curation.models import QuestionCatalog, ValidatedCuratedPassage
from ._internal.available_inputs import (
    discover_curation_paths,
    discover_prepared_source_dirs,
    select_available_curations,
)
from ._internal.database import create_database
from ._internal.embedding_pipeline import resolve_embeddings
from ._internal.hints import DeterministicHintGenerator, PassageTextHintGenerator
from ._internal.manifest import write_manifest
from ._internal.runtime_model import download_runtime_model
from ._internal.splitter import split_document
from ._internal.validation import validate_corpus
from .config import BuilderConfig, load_config


def _normalize_source_dirs(source_dir: Path | Sequence[Path]) -> list[Path]:
    """Normalizes the backward-compatible build API to one or more prepared directories."""
    if isinstance(source_dir, Path):
        return [source_dir]
    result = [Path(value) for value in source_dir]
    if not result:
        raise ValueError("At least one --source is required")
    return result


def _hint_generator(config: BuilderConfig):
    if config.hints.provider == "deterministic":
        return DeterministicHintGenerator()
    if config.hints.provider == "passage_text":
        return PassageTextHintGenerator()
    raise ValueError(f"Unsupported hint provider: {config.hints.provider}")


def _load_guided_inputs(
    *,
    documents: list[SourceDocument],
    questions_path: Path | None,
    curation_paths: list[Path],
) -> tuple[QuestionCatalog | None, list[ValidatedCuratedPassage]]:
    if curation_paths and questions_path is None:
        raise ValueError("--questions is required when --curation is supplied")
    if questions_path is None:
        return None, []

    catalog = load_question_catalog(questions_path)
    curated: list[ValidatedCuratedPassage] = []
    seen_passage_ids: set[str] = set()
    seen_mappings: set[tuple[str, str]] = set()
    for curation_path in curation_paths:
        validated = load_validated_curation_from_documents(
            documents=documents,
            questions_path=questions_path,
            curation_path=curation_path,
        )
        if validated.question_catalog_id != catalog.catalog_id:
            raise ValueError(
                f"Curation {curation_path} uses catalog {validated.question_catalog_id}, "
                f"expected {catalog.catalog_id}"
            )
        for passage in validated.passages:
            if passage.passage_id in seen_passage_ids:
                raise ValueError(
                    f"Duplicate curated passage_id across build inputs: {passage.passage_id}"
                )
            seen_passage_ids.add(passage.passage_id)
            for match in passage.matches:
                mapping = (match.question_id, passage.passage_id)
                if mapping in seen_mappings:
                    raise ValueError(
                        "Duplicate guided question/passage mapping across build inputs: "
                        f"{match.question_id}/{passage.passage_id}"
                    )
                seen_mappings.add(mapping)
            curated.append(passage)

    curated.sort(
        key=lambda passage: (
            passage.work_id,
            passage.text_version_id,
            int(passage.source_locator.split(":")[1]),
            passage.passage_id,
        )
    )
    return catalog, curated


def build_available_corpus(
    config: BuilderConfig,
    source_root: Path,
    output_dir: Path,
    *,
    questions_path: Path | None = None,
    curation_root: Path | None = None,
) -> None:
    """Builds one runtime corpus from every prepared source set currently available locally."""
    source_dirs = discover_prepared_source_dirs(source_root)
    documents = load_prepared_source_sets(source_dirs)
    discovered_curations = discover_curation_paths(curation_root)
    if discovered_curations and questions_path is None:
        raise ValueError("--questions is required when --curation-root contains curated metadata")
    selected_curations, skipped_curations = select_available_curations(
        documents=documents,
        curation_paths=discovered_curations,
    )

    print(
        f"Discovered {len(source_dirs)} prepared source sets under {source_root}:",
        flush=True,
    )
    for source_dir in source_dirs:
        print(f"  {source_dir}", flush=True)
    if curation_root is not None:
        print(
            f"Selected {len(selected_curations)} curated metadata files from {curation_root}.",
            flush=True,
        )
        for path in selected_curations:
            print(f"  {path}", flush=True)
        if skipped_curations:
            print(
                "Skipped curation files whose prepared text versions are not available locally:",
                flush=True,
            )
            for path in skipped_curations:
                print(f"  {path}", flush=True)

    build_corpus(
        config,
        source_dirs,
        output_dir,
        questions_path=questions_path,
        curation_paths=list(selected_curations),
    )


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


def build_corpus(
    config: BuilderConfig,
    source_dir: Path | Sequence[Path],
    output_dir: Path,
    *,
    questions_path: Path | None = None,
    curation_paths: list[Path] | None = None,
) -> None:
    """Builds, validates, and atomically publishes free-form plus optional guided runtime data."""
    curation_paths = list(curation_paths or [])
    source_dirs = _normalize_source_dirs(source_dir)
    print("[1/5] Loading sources, passages, and guided curation...", flush=True)
    documents = load_prepared_source_sets(source_dirs)
    passages = [
        passage
        for document in documents
        for passage in split_document(document, config.passages)
    ]
    question_catalog, curated_passages = _load_guided_inputs(
        documents=documents,
        questions_path=questions_path,
        curation_paths=curation_paths,
    )

    automatic_ids = {passage.passage_id for passage in passages}
    duplicate_ids = automatic_ids.intersection(
        passage.passage_id for passage in curated_passages
    )
    if duplicate_ids:
        raise ValueError(
            "Curated passage IDs conflict with automatic passages: "
            f"{sorted(duplicate_ids)}"
        )

    hint_generator = _hint_generator(config)
    hints = [
        hint
        for passage in passages
        for hint in hint_generator.generate(passage, config.hints.hints_per_passage)
    ]
    guided_mapping_count = sum(len(passage.matches) for passage in curated_passages)

    print(
        f"Prepared {len(documents)} works, {len(passages)} automatic passages, "
        f"{len(curated_passages)} curated passages, {len(hints)} embedding hints, "
        f"{guided_mapping_count} guided mappings.",
        flush=True,
    )
    print("[2/5] Resolving embeddings...", flush=True)
    vectors = resolve_embeddings(config, hints, source_dirs)

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
            question_catalog=question_catalog,
            curated_passages=curated_passages,
        )
        (staging_dir / "vectors.json").write_text(
            json.dumps(vectors, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        write_manifest(
            staging_dir / "manifest.json",
            config=config,
            documents=documents,
            passage_count=len(passages) + len(curated_passages),
            hint_count=len(hints),
            guided_question_count=(len(question_catalog.items) if question_catalog else 0),
            guided_mapping_count=guided_mapping_count,
        )

        print("[4/5] Validating corpus...", flush=True)
        validate_corpus(corpus_path)
        print("[5/5] Publishing corpus...", flush=True)

    print(f"Published corpus: {output_dir}", flush=True)


__all__ = [
    "build_available_corpus",
    "build_corpus",
    "download_runtime_model",
    "inspect_passages",
    "load_config",
    "validate_corpus",
]
