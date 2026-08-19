"""SQLite materialization for automatic and curated runtime corpus artifacts.

Pipeline position:

    canonical documents + automatic passages/hints + validated curated passages
        -> THIS MODULE -> corpus.db

The SQL schema is owned by ``corpus-format/schema.sql``. This writer mirrors that canonical
schema and only persists literary wording supplied by exact prepared-source slices.
"""

import sqlite3
from pathlib import Path

from sibyl_corpus_builder.curation.models import QuestionCatalog, ValidatedCuratedPassage
from sibyl_corpus_core.models import SourceDocument

from .models import PassageCandidate, SemanticHint


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
    source_locator TEXT,
    source_artifact_sha256 TEXT,
    canonical_text_sha256 TEXT,
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

CREATE TABLE guided_question_catalog (
    id TEXT PRIMARY KEY,
    language TEXT NOT NULL
);

CREATE TABLE guided_question (
    id TEXT PRIMARY KEY,
    catalog_id TEXT NOT NULL REFERENCES guided_question_catalog(id),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    kind TEXT NOT NULL CHECK (kind IN ('question', 'state')),
    theme TEXT NOT NULL,
    text TEXT NOT NULL,
    UNIQUE (catalog_id, ordinal)
);

CREATE TABLE guided_question_passage (
    question_id TEXT NOT NULL REFERENCES guided_question(id),
    passage_id TEXT NOT NULL REFERENCES passage(id),
    strength REAL NOT NULL CHECK (strength >= 0.0 AND strength <= 1.0),
    PRIMARY KEY (question_id, passage_id)
);

CREATE INDEX idx_text_version_work ON text_version(work_id);
CREATE INDEX idx_passage_work ON passage(work_id);
CREATE INDEX idx_passage_text_passage ON passage_text(passage_id);
CREATE INDEX idx_passage_text_version ON passage_text(text_version_id);
CREATE INDEX idx_hint_passage ON semantic_hint(passage_id);
CREATE INDEX idx_guided_question_catalog ON guided_question(catalog_id, ordinal);
CREATE INDEX idx_guided_mapping_passage ON guided_question_passage(passage_id);"""


def create_database(
    path: Path,
    *,
    format_version: int,
    language: str,
    embedding_provider: str,
    embedding_model: str | None,
    embedding_dimensions: int,
    documents: list[SourceDocument],
    passages: list[PassageCandidate],
    hints: list[SemanticHint],
    question_catalog: QuestionCatalog | None = None,
    curated_passages: list[ValidatedCuratedPassage] | None = None,
) -> None:
    """Materializes the format-owned SQLite corpus from exact automatic and curated passages."""
    curated_passages = curated_passages or []
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)

    metadata = [
        ("format_version", str(format_version)),
        ("language", language),
        ("embedding_provider", embedding_provider),
        ("embedding_dimensions", str(embedding_dimensions)),
    ]
    if embedding_model:
        metadata.append(("embedding_model", embedding_model))

    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata)

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
                    translation_model, source_name, source_uri, source_locator,
                    source_artifact_sha256, canonical_text_sha256, rights_status,
                    rights_jurisdiction, provenance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    document.source_locator,
                    document.source_artifact_sha256,
                    document.canonical_text_sha256,
                    document.rights_status,
                    document.rights_jurisdiction,
                    document.provenance,
                ),
            )

        next_ordinal_by_work: dict[str, int] = {}
        for passage in passages:
            connection.execute(
                """
                INSERT INTO passage(
                    id, work_id, ordinal, source_locator, quality_score,
                    context_dependency, spoiler_risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    passage.passage_id,
                    passage.source_id,
                    passage.ordinal,
                    passage.source_locator,
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
                    passage.source_locator,
                ),
            )
            next_ordinal_by_work[passage.source_id] = max(
                next_ordinal_by_work.get(passage.source_id, 0), passage.ordinal + 1
            )

        connection.executemany(
            "INSERT INTO semantic_hint(id, passage_id, text) VALUES (?, ?, ?)",
            [(hint.hint_id, hint.passage_id, hint.text) for hint in hints],
        )

        if question_catalog is not None:
            connection.execute(
                "INSERT INTO guided_question_catalog(id, language) VALUES (?, ?)",
                (question_catalog.catalog_id, question_catalog.language),
            )
            connection.executemany(
                """
                INSERT INTO guided_question(id, catalog_id, ordinal, kind, theme, text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        question.id,
                        question_catalog.catalog_id,
                        ordinal,
                        question.kind,
                        question.theme,
                        question.text,
                    )
                    for ordinal, question in enumerate(question_catalog.items)
                ],
            )

        for curated in curated_passages:
            ordinal = next_ordinal_by_work.get(curated.work_id, 0)
            next_ordinal_by_work[curated.work_id] = ordinal + 1
            connection.execute(
                """
                INSERT INTO passage(
                    id, work_id, ordinal, source_locator, quality_score,
                    context_dependency, spoiler_risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    curated.passage_id,
                    curated.work_id,
                    ordinal,
                    curated.source_locator,
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
                    curated.passage_id,
                    curated.text_version_id,
                    "standard",
                    curated.text,
                    curated.word_count,
                    curated.source_locator,
                ),
            )
            connection.executemany(
                """
                INSERT INTO guided_question_passage(question_id, passage_id, strength)
                VALUES (?, ?, ?)
                """,
                [
                    (match.question_id, curated.passage_id, match.strength)
                    for match in curated.matches
                ],
            )
