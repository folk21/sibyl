PRAGMA foreign_keys = ON;

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
CREATE INDEX idx_hint_passage ON semantic_hint(passage_id);
