import hashlib
import json
import shutil
import sys
from pathlib import Path

from .config import BuilderConfig
from .database import create_database
from .embedding_cache import EmbeddingCache
from .embeddings import HashEmbeddingProvider, SentenceTransformerEmbeddingProvider
from .hints import DeterministicHintGenerator, PassageTextHintGenerator
from .models import SemanticHint
from .source_loader import load_sources
from .splitter import split_document
from .validation import validate_corpus


def _hint_generator(config: BuilderConfig):
    if config.hints.provider == "deterministic":
        return DeterministicHintGenerator()
    if config.hints.provider == "passage_text":
        return PassageTextHintGenerator()
    raise ValueError(f"Unsupported hint provider: {config.hints.provider}")


def _embedding_provider(config: BuilderConfig):
    embedding = config.embeddings
    if embedding.provider == "hash":
        return HashEmbeddingProvider(dimensions=embedding.dimensions, normalize=embedding.normalize)
    if embedding.provider == "sentence_transformers":
        assert embedding.model_id is not None
        return SentenceTransformerEmbeddingProvider(
            model_id=embedding.model_id,
            dimensions=embedding.dimensions,
            normalize=embedding.normalize,
            passage_prefix=embedding.passage_prefix,
        )
    raise ValueError(f"Unsupported embedding provider: {embedding.provider}")


def _embedding_fingerprint(config: BuilderConfig) -> str:
    embedding = config.embeddings
    payload = {
        "provider": embedding.provider,
        "model_id": embedding.model_id,
        "dimensions": embedding.dimensions,
        "normalize": embedding.normalize,
        "passage_prefix": embedding.passage_prefix,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:20]


def _text_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _render_progress(completed: int, total: int) -> None:
    if total <= 0:
        return
    width = 36
    fraction = min(1.0, completed / total)
    filled = int(width * fraction)
    bar = "█" * filled + "·" * (width - filled)
    percent = fraction * 100
    print(
        f"\rEmbedding passages [{bar}] {completed}/{total} ({percent:5.1f}%)",
        end="" if completed < total else "\n",
        file=sys.stdout,
        flush=True,
    )


def _resolve_embeddings(
    config: BuilderConfig,
    hints: list[SemanticHint],
    source_dir: Path,
) -> dict[str, list[float]]:
    """Reuses cached vectors and computes missing embedding batches with visible progress."""
    unique_inputs: dict[str, str] = {}
    hint_keys: dict[str, str] = {}
    for hint in hints:
        key = _text_key(hint.text)
        unique_inputs.setdefault(key, hint.text)
        hint_keys[hint.hint_id] = key

    cache_path = (
        source_dir / ".embedding-cache" / f"{_embedding_fingerprint(config)}.sqlite3"
    )
    cached: dict[str, list[float]] = {}

    cache: EmbeddingCache | None = None
    try:
        if config.embeddings.cache:
            cache = EmbeddingCache(cache_path, config.embeddings.dimensions)
            cached = cache.get_many(list(unique_inputs))

        missing_keys = [key for key in unique_inputs if key not in cached]
        print(
            "Embedding inputs: "
            f"{len(unique_inputs)} unique ({len(hints)} hints), "
            f"{len(cached)} cached, {len(missing_keys)} to compute.",
            flush=True,
        )
        if config.embeddings.cache:
            print(f"Embedding cache: {cache_path}", flush=True)

        if missing_keys:
            model_label = config.embeddings.model_id or config.embeddings.provider
            print(f"Loading embedding provider: {model_label}", flush=True)
            provider = _embedding_provider(config)
            if provider.dimensions != config.embeddings.dimensions:
                raise ValueError(
                    f"Embedding provider dimensions {provider.dimensions} do not match "
                    f"configured {config.embeddings.dimensions}"
                )

            batch_size = config.embeddings.batch_size
            _render_progress(len(cached), len(unique_inputs))
            for start in range(0, len(missing_keys), batch_size):
                batch_keys = missing_keys[start : start + batch_size]
                batch_texts = [unique_inputs[key] for key in batch_keys]
                batch_vectors = provider.embed_many(batch_texts, batch_size=batch_size)
                if len(batch_vectors) != len(batch_keys):
                    raise ValueError(
                        "Embedding provider returned a different number of vectors than inputs"
                    )
                batch = dict(zip(batch_keys, batch_vectors, strict=True))
                if cache is not None:
                    cache.put_many(batch)
                cached.update(batch)
                _render_progress(len(cached), len(unique_inputs))
        else:
            _render_progress(len(cached), len(unique_inputs))

        if len(cached) != len(unique_inputs):
            raise ValueError("Embedding generation did not produce all required vectors")
        return {hint.hint_id: cached[hint_keys[hint.hint_id]] for hint in hints}
    finally:
        if cache is not None:
            cache.close()


def build_corpus(config: BuilderConfig, source_dir: Path, output_dir: Path) -> None:
    """Builds, validates, and atomically publishes a corpus from prepared source documents."""
    print("[1/5] Loading sources and extracting passages...", flush=True)
    documents = load_sources(source_dir)
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
    vectors = _resolve_embeddings(config, hints, source_dir.resolve())

    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    try:
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

        print("[4/5] Validating corpus...", flush=True)
        validate_corpus(corpus_path)

        print("[5/5] Publishing corpus...", flush=True)
        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging_dir.rename(output_dir)
        print(f"Published corpus: {output_dir}", flush=True)
    except BaseException:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise
