"""Typed configuration for the automatic passage/embedding corpus build feature."""

from dataclasses import dataclass
from pathlib import Path
import tomllib

_CURRENT_FORMAT_VERSION = 4


@dataclass(frozen=True)
class PassageConfig:
    """Controls deterministic automatic passage boundary and overlap sizing."""

    min_words: int
    preferred_words: int
    max_words: int
    overlap_paragraphs: int


@dataclass(frozen=True)
class HintConfig:
    """Selects the semantic-hint strategy used before automatic-build embeddings."""

    provider: str
    hints_per_passage: int


@dataclass(frozen=True)
class EmbeddingConfig:
    """Defines the build-time embedding contract later checked by runtime manifests."""

    provider: str
    dimensions: int
    normalize: bool
    model_id: str | None = None
    passage_prefix: str = ""
    query_prefix: str = ""
    batch_size: int = 32
    cache: bool = True


@dataclass(frozen=True)
class BuilderConfig:
    """Aggregates format, language, automatic passage, hint, and embedding settings."""

    format_version: int
    language: str
    passages: PassageConfig
    hints: HintConfig
    embeddings: EmbeddingConfig


def load_config(path: Path) -> BuilderConfig:
    """Loads TOML into immutable settings and rejects inconsistent values before heavy work."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    passages = PassageConfig(**raw["passages"])
    raw_hints = raw["hints"]
    hints = HintConfig(
        provider=str(raw_hints.get("provider", "deterministic")),
        hints_per_passage=int(raw_hints["hints_per_passage"]),
    )
    raw_embeddings = raw["embeddings"]
    embeddings = EmbeddingConfig(
        provider=str(raw_embeddings["provider"]),
        dimensions=int(raw_embeddings["dimensions"]),
        normalize=bool(raw_embeddings["normalize"]),
        model_id=raw_embeddings.get("model_id"),
        passage_prefix=str(raw_embeddings.get("passage_prefix", "")),
        query_prefix=str(raw_embeddings.get("query_prefix", "")),
        batch_size=int(raw_embeddings.get("batch_size", 32)),
        cache=bool(raw_embeddings.get("cache", True)),
    )
    config = BuilderConfig(
        format_version=int(raw["corpus"]["format_version"]),
        language=str(raw["corpus"]["language"]),
        passages=passages,
        hints=hints,
        embeddings=embeddings,
    )
    validate_config(config)
    return config


def validate_config(config: BuilderConfig) -> None:
    """Rejects inconsistent automatic-build settings before network/model/disk-heavy work."""
    if config.format_version != _CURRENT_FORMAT_VERSION:
        raise ValueError(
            f"corpus.format_version must be {_CURRENT_FORMAT_VERSION}; got {config.format_version}"
        )
    p = config.passages
    if p.min_words <= 0:
        raise ValueError("passages.min_words must be positive")
    if not p.min_words <= p.preferred_words <= p.max_words:
        raise ValueError("passage word limits must satisfy min <= preferred <= max")
    if p.overlap_paragraphs < 0:
        raise ValueError("passages.overlap_paragraphs must not be negative")
    if config.hints.hints_per_passage <= 0:
        raise ValueError("hints.hints_per_passage must be positive")
    if config.hints.provider not in {"deterministic", "passage_text"}:
        raise ValueError(f"Unsupported hints.provider: {config.hints.provider}")
    if config.embeddings.dimensions <= 0:
        raise ValueError("embeddings.dimensions must be positive")
    if config.embeddings.batch_size <= 0:
        raise ValueError("embeddings.batch_size must be positive")
    if config.embeddings.provider == "sentence_transformers" and not config.embeddings.model_id:
        raise ValueError("embeddings.model_id is required for sentence_transformers")
