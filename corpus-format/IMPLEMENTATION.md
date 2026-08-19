# Corpus format implementation

## Scope

`corpus-format/` is the persisted compatibility contract between corpus construction and runtime readers. It contains no source acquisition, literary curation, or retrieval ranking logic.

Current format version: **4**.

## Owning files

- `VERSION` — integer current format version emitted by the builder;
- `schema.sql` — canonical relational schema semantics;
- `manifest.schema.json` — current JSON manifest contract;
- `tools/validate_schema.py` — self-check for required SQL tables/constraints and VERSION/schema consistency.

Detailed field semantics and migration behavior live in [`../docs/CORPUS_FORMAT.md`](../docs/CORPUS_FORMAT.md).

## Runtime artifact relationship

A current published corpus is represented by:

```text
manifest.json
corpus.db
vectors.json
```

`corpus.db` persists authors, works, text versions, exact passages/texts, semantic hints, guided-question catalog rows, and guided question/passage mappings. `vectors.json` maps semantic-hint IDs to embedding vectors for the current free-form development implementation. `manifest.json` records format/embedding compatibility information plus artifact filenames and counts.

## Writer and reader locations

The format package defines the contract, while concrete code lives elsewhere:

- Python writer: `corpus-builder/src/sibyl_corpus_builder/build/_internal/database.py` and `build/api.py`;
- Python corpus validation: `corpus-builder/src/sibyl_corpus_builder/build/_internal/validation.py`;
- Desktop manifest reader: `mobile/desktopApp/.../RuntimeManifests.kt`;
- Desktop SQLite reader: `mobile/desktopApp/.../SqliteCorpusRepository.kt`.

Because writer and readers are implemented in separate projects, format changes must inspect all of them before publication.

## Exact-text relationship

`passage` identifies a semantic location in a work. `passage_text` stores the concrete text for one text version and prepared length. Both automatic and curated runtime passages use this representation; displayed literary text must come from `passage_text.text` rather than generated semantic/curation metadata.

`semantic_hint` is free-form retrieval metadata. `guided_question_passage.strength` is guided curated relevance. Neither becomes quotation text.

## Version compatibility

New builder output is v4. Desktop currently accepts v3 and v4 so existing development corpora can continue free-form retrieval; guided lookup is available only from v4 persisted tables. Unknown versions are rejected before runtime resources are opened.
