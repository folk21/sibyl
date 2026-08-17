"""Embedding providers for the automatic corpus-build path.

Only explicit build commands instantiate semantic models. Importing this module never downloads
or loads a model; ``SentenceTransformerEmbeddingProvider`` performs that work in its constructor.
"""

import hashlib
import math
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Build-time contract for deterministic or semantic batch embedding providers."""

    @property
    def dimensions(self) -> int: ...

    @property
    def model_id(self) -> str | None: ...

    def embed_many(self, texts: list[str], *, batch_size: int) -> list[list[float]]: ...


class HashEmbeddingProvider:
    """Deterministic development vectors. They are not semantic production embeddings."""

    def __init__(self, dimensions: int, normalize: bool = True) -> None:
        self._dimensions = dimensions
        self._normalize = normalize

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_id(self) -> str | None:
        return None

    def embed_many(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        del batch_size
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self._dimensions:
            digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) == self._dimensions:
                    break
            counter += 1

        if self._normalize:
            norm = math.sqrt(sum(value * value for value in values)) or 1.0
            values = [value / norm for value in values]
        return values


class SentenceTransformerEmbeddingProvider:
    """Opt-in build-time semantic embeddings; importing the package never downloads a model."""

    def __init__(
        self,
        *,
        model_id: str,
        dimensions: int,
        normalize: bool,
        passage_prefix: str = "",
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise ValueError(
                "sentence-transformers is not installed. "
                "Install corpus-builder with the 'ml' extra."
            ) from error
        self._model_id = model_id
        self._model = SentenceTransformer(model_id)
        detected = self._model.get_sentence_embedding_dimension()
        if detected is not None and int(detected) != dimensions:
            raise ValueError(
                f"Embedding dimension mismatch for {model_id}: "
                f"configured {dimensions}, model {detected}"
            )
        self._dimensions = dimensions
        self._normalize = normalize
        self._passage_prefix = passage_prefix

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_id(self) -> str | None:
        return self._model_id

    def embed_many(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        """Encode passage-prefixed batches and enforce configured vector dimensions."""
        if not texts:
            return []
        vectors = self._model.encode(
            [self._passage_prefix + text for text in texts],
            batch_size=batch_size,
            normalize_embeddings=self._normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        result: list[list[float]] = []
        for vector in vectors:
            values = vector.tolist()
            if len(values) != self._dimensions:
                raise ValueError(
                    f"Embedding provider returned {len(values)} dimensions, "
                    f"expected {self._dimensions}"
                )
            result.append([float(value) for value in values])
        return result
