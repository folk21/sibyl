"""Embedding orchestration for the automatic corpus-build path.

This module sits between semantic hints and persisted vectors. It owns provider selection,
configuration fingerprints, resumable cache lookups, batching, and progress output. Multi-source
builds read compatible caches from every prepared input directory and write newly computed
vectors to the first source cache. It does not select passages or write runtime corpus artifacts.
"""

import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ..config import BuilderConfig
from .embedding_cache import EmbeddingCache
from .embeddings import HashEmbeddingProvider, SentenceTransformerEmbeddingProvider
from .models import SemanticHint


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


def _normalize_source_dirs(source_dir: Path | Sequence[Path]) -> list[Path]:
    if isinstance(source_dir, Path):
        return [source_dir]
    result = [Path(value) for value in source_dir]
    if not result:
        raise ValueError("At least one embedding cache source directory is required")
    return result


def _load_cache_hits(
    *,
    cache_paths: list[Path],
    keys: list[str],
    dimensions: int,
) -> dict[str, list[float]]:
    """Loads each requested exact-text vector from the first compatible source cache that has it."""
    found: dict[str, list[float]] = {}
    for path in cache_paths:
        if not path.is_file():
            continue
        missing = [key for key in keys if key not in found]
        if not missing:
            break
        with EmbeddingCache(path, dimensions) as cache:
            found.update(cache.get_many(missing))
    return found


def resolve_embeddings(
    config: BuilderConfig,
    hints: list[SemanticHint],
    source_dir: Path | Sequence[Path],
) -> dict[str, list[float]]:
    """Reuses all compatible source caches and computes only missing exact embedding inputs."""
    unique_inputs: dict[str, str] = {}
    hint_keys: dict[str, str] = {}
    for hint in hints:
        key = _text_key(hint.text)
        unique_inputs.setdefault(key, hint.text)
        hint_keys[hint.hint_id] = key

    source_dirs = _normalize_source_dirs(source_dir)
    fingerprint = _embedding_fingerprint(config)
    cache_paths = [
        directory.resolve() / ".embedding-cache" / f"{fingerprint}.sqlite3"
        for directory in source_dirs
    ]
    cached: dict[str, list[float]] = {}

    primary_cache: EmbeddingCache | None = None
    try:
        if config.embeddings.cache:
            cached = _load_cache_hits(
                cache_paths=cache_paths,
                keys=list(unique_inputs),
                dimensions=config.embeddings.dimensions,
            )
            primary_cache = EmbeddingCache(cache_paths[0], config.embeddings.dimensions)

        missing_keys = [key for key in unique_inputs if key not in cached]
        print(
            "Embedding inputs: "
            f"{len(unique_inputs)} unique ({len(hints)} hints), "
            f"{len(cached)} cached, {len(missing_keys)} to compute.",
            flush=True,
        )
        if config.embeddings.cache:
            print("Embedding cache sources:", flush=True)
            for cache_path in cache_paths:
                print(f"  {cache_path}", flush=True)
            if len(cache_paths) > 1:
                print(f"Embedding cache writes: {cache_paths[0]}", flush=True)

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
                if primary_cache is not None:
                    primary_cache.put_many(batch)
                cached.update(batch)
                _render_progress(len(cached), len(unique_inputs))
        else:
            _render_progress(len(cached), len(unique_inputs))

        if len(cached) != len(unique_inputs):
            raise ValueError("Embedding generation did not produce all required vectors")
        return {hint.hint_id: cached[hint_keys[hint.hint_id]] for hint in hints}
    finally:
        if primary_cache is not None:
            primary_cache.close()
