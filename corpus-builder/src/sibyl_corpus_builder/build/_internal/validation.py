"""Post-write validation for the persisted runtime corpus database.

This is the final correctness gate before build output is atomically published. It checks
foreign keys, required metadata, non-empty free-form retrieval content, and format-v4 guided
relationships when present.
"""

import sqlite3
from pathlib import Path

_CURRENT_FORMAT_VERSION = 4


def validate_corpus(path: Path) -> None:
    """Validates required corpus metadata, foreign keys, and persisted retrieval/display content."""
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

        if int(metadata["format_version"]) != _CURRENT_FORMAT_VERSION:
            raise ValueError(
                "Builder validation requires corpus format "
                f"{_CURRENT_FORMAT_VERSION}, got {metadata['format_version']}"
            )
        if int(metadata["embedding_dimensions"]) <= 0:
            raise ValueError("Embedding dimensions must be positive")

        passages = connection.execute("SELECT COUNT(*) FROM passage").fetchone()[0]
        variants = connection.execute("SELECT COUNT(*) FROM passage_text").fetchone()[0]
        hints = connection.execute("SELECT COUNT(*) FROM semantic_hint").fetchone()[0]
        if passages <= 0 or variants <= 0 or hints <= 0:
            raise ValueError("Corpus must contain passages, passage texts, and semantic hints")

        guided_tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            if row[0].startswith("guided_question")
        }
        expected_guided = {
            "guided_question_catalog",
            "guided_question",
            "guided_question_passage",
        }
        if guided_tables != expected_guided:
            raise ValueError("Corpus format v4 requires the complete guided-question schema")

        invalid_strengths = connection.execute(
            "SELECT COUNT(*) FROM guided_question_passage WHERE strength < 0.0 OR strength > 1.0"
        ).fetchone()[0]
        if invalid_strengths:
            raise ValueError("Corpus contains guided mapping strengths outside [0, 1]")
