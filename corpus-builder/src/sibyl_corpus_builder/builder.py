import json
import shutil
from pathlib import Path

from .config import BuilderConfig
from .database import create_database
from .embeddings import HashEmbeddingProvider
from .hints import DeterministicHintGenerator
from .source_loader import load_sources
from .splitter import split_document
from .validation import validate_corpus


def build_corpus(config: BuilderConfig, source_dir: Path, output_dir: Path) -> None:
    documents = load_sources(source_dir)
    passages = [
        passage
        for document in documents
        for passage in split_document(document, config.passages)
    ]

    hint_generator = DeterministicHintGenerator()
    hints = [
        hint
        for passage in passages
        for hint in hint_generator.generate(passage, config.hints_per_passage)
    ]

    if config.embeddings.provider != "hash":
        raise ValueError(
            "The initial builder implements only the deterministic 'hash' provider. "
            "Production providers must be added explicitly."
        )
    embedding_provider = HashEmbeddingProvider(
        dimensions=config.embeddings.dimensions,
        normalize=config.embeddings.normalize,
    )

    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    try:
        corpus_path = staging_dir / "corpus.db"
        create_database(
            corpus_path,
            format_version=config.format_version,
            language=config.language,
            embedding_provider=config.embeddings.provider,
            embedding_dimensions=embedding_provider.dimensions,
            documents=documents,
            passages=passages,
            hints=hints,
        )

        vectors = {hint.hint_id: embedding_provider.embed(hint.text) for hint in hints}
        (staging_dir / "vectors.json").write_text(
            json.dumps(vectors, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        manifest = {
            "format_version": config.format_version,
            "language": config.language,
            "embedding": {
                "provider": config.embeddings.provider,
                "dimensions": embedding_provider.dimensions,
                "normalize": config.embeddings.normalize,
            },
            "content": {
                "target_language": config.language,
                "source_languages": sorted({document.language for document in documents}),
                "categories": sorted({document.category for document in documents}),
            },
            "counts": {
                "works": len(documents),
                "passages": len(passages),
                "hints": len(hints),
            },
            "artifacts": {
                "corpus": "corpus.db",
                "vectors": "vectors.json",
            },
        }
        (staging_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        validate_corpus(corpus_path)

        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging_dir.rename(output_dir)
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise
