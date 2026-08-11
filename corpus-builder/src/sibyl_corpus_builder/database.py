import sqlite3
from pathlib import Path

from .models import PassageCandidate, SemanticHint, SourceDocument


SCHEMA = r"""PRAGMA foreign_keys = ON;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE author (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);

CREATE TABLE work (
    id TEXT PRIMARY KEY,
    author_id TEXT NOT NULL REFERENCES author(id),
    title TEXT NOT NULL,
    original_language TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('literature', 'philosophy', 'sacred_text'))
);

CREATE TABLE text_version (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL REFERENCES work(id),
    language TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('original', 'human_translation', 'machine_translation')),
    translator TEXT,
    translation_provider TEXT,
    translation_model TEXT,
    edition_label TEXT,
    edition_year INTEGER,
    source_name TEXT NOT NULL,
    source_uri TEXT,
    rights_status TEXT,
    rights_jurisdiction TEXT,
    provenance TEXT
);

CREATE TABLE passage (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL REFERENCES work(id),
    ordinal INTEGER NOT NULL,
    source_locator TEXT NOT NULL,
    quality_score REAL,
    context_dependency REAL,
    spoiler_risk REAL
);

CREATE TABLE passage_text (
    passage_id TEXT NOT NULL REFERENCES passage(id),
    text_version_id TEXT NOT NULL REFERENCES text_version(id),
    variant TEXT NOT NULL CHECK (variant IN ('short', 'standard', 'extended')),
    text TEXT NOT NULL,
    word_count INTEGER NOT NULL CHECK (word_count > 0),
    source_locator TEXT,
    PRIMARY KEY (passage_id, text_version_id, variant)
);

CREATE TABLE semantic_hint (
    id TEXT PRIMARY KEY,
    passage_id TEXT NOT NULL REFERENCES passage(id),
    text TEXT NOT NULL,
    semantic_cluster TEXT
);

CREATE INDEX idx_text_version_work ON text_version(work_id);
CREATE INDEX idx_passage_work ON passage(work_id);
CREATE INDEX idx_passage_text_passage ON passage_text(passage_id);
CREATE INDEX idx_passage_text_version ON passage_text(text_version_id);
CREATE INDEX idx_hint_passage ON semantic_hint(passage_id);"""


def create_database(
    path: Path,
    *,
    format_version: int,
    language: str,
    embedding_provider: str,
    embedding_dimensions: int,
    documents: list[SourceDocument],
    passages: list[PassageCandidate],
    hints: list[SemanticHint],
) -> None:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [
                ("format_version", str(format_version)),
                ("language", language),
                ("embedding_provider", embedding_provider),
                ("embedding_dimensions", str(embedding_dimensions)),
            ],
        )

        for document in documents:
            author_id = f"a_{document.source_id}"
            connection.execute(
                "INSERT OR IGNORE INTO author(id, display_name) VALUES (?, ?)",
                (author_id, document.author),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO work(id, author_id, title, original_language, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document.source_id,
                    author_id,
                    document.work,
                    document.original_language,
                    document.category,
                ),
            )
            connection.execute(
                """
                INSERT INTO text_version(
                    id, work_id, language, role, translator, translation_provider,
                    translation_model, source_name, source_uri, rights_status,
                    rights_jurisdiction, provenance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document.text_version_id,
                    document.source_id,
                    document.language,
                    document.text_role,
                    document.translator,
                    document.translation_provider,
                    document.translation_model,
                    document.source_name,
                    document.source_uri,
                    document.rights_status,
                    document.rights_jurisdiction,
                    document.provenance,
                ),
            )

        for passage in passages:
            connection.execute(
                """
                INSERT INTO passage(
                    id, work_id, ordinal, source_locator, quality_score, context_dependency, spoiler_risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    passage.passage_id,
                    passage.source_id,
                    passage.ordinal,
                    f"ordinal:{passage.ordinal}",
                    None,
                    None,
                    None,
                ),
            )
            connection.execute(
                """
                INSERT INTO passage_text(
                    passage_id, text_version_id, variant, text, word_count, source_locator
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    passage.passage_id,
                    passage.text_version_id,
                    "standard",
                    passage.text,
                    passage.word_count,
                    f"ordinal:{passage.ordinal}",
                ),
            )

        connection.executemany(
            "INSERT INTO semantic_hint(id, passage_id, text) VALUES (?, ?, ?)",
            [(hint.hint_id, hint.passage_id, hint.text) for hint in hints],
        )
