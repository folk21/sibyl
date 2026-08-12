# Sibyl corpus format

`corpus-format/` defines the versioned persisted contract between the Python builder and the mobile runtime.

Current format: **3**.

Canonical files:

- [`VERSION`](VERSION);
- [`schema.sql`](schema.sql);
- [`manifest.schema.json`](manifest.schema.json);
- [`tools/validate_schema.py`](tools/validate_schema.py).

Validate locally:

```bash
python tools/validate_schema.py
```

A mobile application may read only format versions it explicitly supports. Builder and mobile assumptions must never drift from this contract.

Detailed semantics, versioning, and validation requirements live in [`../docs/CORPUS_FORMAT.md`](../docs/CORPUS_FORMAT.md). See also [`AGENTS.md`](AGENTS.md).
