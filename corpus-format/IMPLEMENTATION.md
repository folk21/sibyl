# Corpus format implementation

## Scope

`corpus-format/` is the persisted compatibility contract between corpus construction and runtime readers. It contains no source acquisition or retrieval ranking logic.

Current format version: **3**.

## Owning files

- `VERSION` — integer format version understood by builder/readers;
- `schema.sql` — canonical relational schema semantics;
- `manifest.schema.json` — JSON manifest contract;
- `tools/validate_schema.py` — self-check for required SQL tables and VERSION/schema consistency.

Detailed field semantics and versioning rules live in [`../docs/CORPUS_FORMAT.md`](../docs/CORPUS_FORMAT.md).

## Runtime artifact relationship

A current published corpus is represented by:

```text
manifest.json
corpus.db
vectors.json
```

`corpus.db` persists authors, works, text versions, semantic passages, exact passage texts, and semantic hints. `vectors.json` maps hint IDs to embedding vectors in the current development implementation. `manifest.json` records format and embedding compatibility information plus artifact filenames/counts.

## Writer and reader locations

The format package defines the contract, while concrete code lives elsewhere:

- Python writer: `corpus-builder/src/sibyl_corpus_builder/database.py` and `builder.py`;
- Python corpus validation: `corpus-builder/src/sibyl_corpus_builder/validation.py`;
- Desktop manifest reader: `mobile/desktopApp/.../RuntimeManifests.kt`;
- Desktop SQLite reader: `mobile/desktopApp/.../SqliteCorpusRepository.kt`.

Because writer and readers are implemented in separate projects, format changes must inspect all of them before publication.

## Exact-text relationship

`passage` identifies a semantic location in a work. `passage_text` stores the concrete text for one text version and prepared length. Displayed literary text must come from `passage_text.text` rather than generated semantic metadata.

`semantic_hint` is intentionally separate. It can change retrieval behavior without becoming display text.

## Version compatibility

Additive optional manifest metadata may remain compatible when old readers can safely ignore it. Changes that alter required persisted semantics, remove/rename required fields, or change identity relationships require a new format version.

Desktop currently rejects unsupported format versions before opening runtime resources.
