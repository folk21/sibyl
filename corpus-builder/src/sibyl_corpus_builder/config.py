from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class PassageConfig:
    min_words: int
    preferred_words: int
    max_words: int
    overlap_paragraphs: int


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    dimensions: int
    normalize: bool


@dataclass(frozen=True)
class BuilderConfig:
    format_version: int
    language: str
    passages: PassageConfig
    hints_per_passage: int
    embeddings: EmbeddingConfig


def load_config(path: Path) -> BuilderConfig:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    passages = PassageConfig(**raw["passages"])
    embeddings = EmbeddingConfig(**raw["embeddings"])
    config = BuilderConfig(
        format_version=int(raw["corpus"]["format_version"]),
        language=str(raw["corpus"]["language"]),
        passages=passages,
        hints_per_passage=int(raw["hints"]["hints_per_passage"]),
        embeddings=embeddings,
    )
    validate_config(config)
    return config


def validate_config(config: BuilderConfig) -> None:
    p = config.passages
    if p.min_words <= 0:
        raise ValueError("passages.min_words must be positive")
    if not p.min_words <= p.preferred_words <= p.max_words:
        raise ValueError("passage word limits must satisfy min <= preferred <= max")
    if p.overlap_paragraphs < 0:
        raise ValueError("passages.overlap_paragraphs must not be negative")
    if config.hints_per_passage <= 0:
        raise ValueError("hints.hints_per_passage must be positive")
    if config.embeddings.dimensions <= 0:
        raise ValueError("embeddings.dimensions must be positive")
