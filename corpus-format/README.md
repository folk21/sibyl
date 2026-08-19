# Sibyl corpus format

`corpus-format/` defines the versioned persisted contract between the Python builder and application runtime.

Current format: **4**.

Canonical files:

- [`VERSION`](VERSION);
- [`schema.sql`](schema.sql);
- [`manifest.schema.json`](manifest.schema.json);
- [`tools/validate_schema.py`](tools/validate_schema.py).

Format v4 keeps the free-form work/text-version/passage/hint model and adds persisted guided-question catalog plus question-to-passage mappings. Curated literary wording still lives only in normal `passage_text` rows.

Validate locally:

```bash
python tools/validate_schema.py
```

A runtime may read only format versions it explicitly supports. Builder and mobile assumptions must never drift from this contract.

Detailed semantics, versioning, and validation requirements live in [`../docs/CORPUS_FORMAT.md`](../docs/CORPUS_FORMAT.md). Concrete writer/reader file mapping is in [`IMPLEMENTATION.md`](IMPLEMENTATION.md). See also [`AGENTS.md`](AGENTS.md).
