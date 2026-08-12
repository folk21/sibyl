import json
import sqlite3
from pathlib import Path


class EmbeddingCache:
    """Persistent build cache keyed by exact embedding input text hashes."""

    def __init__(self, path: Path, dimensions: int) -> None:
        self._path = path
        self._dimensions = dimensions
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_sha256 TEXT PRIMARY KEY,
                dimensions INTEGER NOT NULL,
                vector_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "EmbeddingCache":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def get_many(self, keys: list[str]) -> dict[str, list[float]]:
        if not keys:
            return {}
        found: dict[str, list[float]] = {}
        cursor = self._connection.cursor()
        for key in keys:
            row = cursor.execute(
                "SELECT dimensions, vector_json FROM embedding_cache WHERE text_sha256 = ?",
                (key,),
            ).fetchone()
            if row is None or int(row[0]) != self._dimensions:
                continue
            try:
                vector = json.loads(str(row[1]))
                if not isinstance(vector, list) or len(vector) != self._dimensions:
                    continue
                found[key] = [float(value) for value in vector]
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return found

    def put_many(self, vectors: dict[str, list[float]]) -> None:
        if not vectors:
            return
        rows = []
        for key, vector in vectors.items():
            if len(vector) != self._dimensions:
                raise ValueError(
                    f"Cannot cache {len(vector)}-dimensional vector; expected {self._dimensions}"
                )
            rows.append(
                (
                    key,
                    self._dimensions,
                    json.dumps(vector, ensure_ascii=False, separators=(",", ":")),
                )
            )
        self._connection.executemany(
            """
            INSERT INTO embedding_cache(text_sha256, dimensions, vector_json)
            VALUES (?, ?, ?)
            ON CONFLICT(text_sha256) DO UPDATE SET
                dimensions = excluded.dimensions,
                vector_json = excluded.vector_json
            """,
            rows,
        )
        self._connection.commit()
