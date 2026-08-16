import sqlite3
from pathlib import Path


def validate_corpus(path: Path) -> None:
    """Validates required corpus metadata, foreign keys, and non-empty persisted content."""
    if not path.is_file():
        raise ValueError(f"Corpus database does not exist: {path}")

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ValueError(f"Corpus has foreign-key violations: {violations}")

        metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
        required = {"format_version", "language", "embedding_provider", "embedding_dimensions"}
        missing = required - metadata.keys()
        if missing:
            raise ValueError(f"Corpus metadata is missing keys: {sorted(missing)}")

        if int(metadata["format_version"]) <= 0:
            raise ValueError("Corpus format version must be positive")
        if int(metadata["embedding_dimensions"]) <= 0:
            raise ValueError("Embedding dimensions must be positive")

        passages = connection.execute("SELECT COUNT(*) FROM passage").fetchone()[0]
        variants = connection.execute("SELECT COUNT(*) FROM passage_text").fetchone()[0]
        hints = connection.execute("SELECT COUNT(*) FROM semantic_hint").fetchone()[0]
        if passages <= 0 or variants <= 0 or hints <= 0:
            raise ValueError("Corpus must contain passages, passage texts, and semantic hints")
