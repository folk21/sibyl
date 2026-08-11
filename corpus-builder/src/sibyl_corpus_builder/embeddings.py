import hashlib
import math
from typing import Protocol


class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    def embed(self, text: str) -> list[float]: ...


class HashEmbeddingProvider:
    """Deterministic development vectors. They are not semantic production embeddings."""

    def __init__(self, dimensions: int, normalize: bool = True) -> None:
        self._dimensions = dimensions
        self._normalize = normalize

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
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
