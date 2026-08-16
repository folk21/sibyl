# Corpus format development rules

Root `AGENTS.md` also applies.

## Ownership

`corpus-format/` owns persisted corpus semantics. Changes may require coordinated builder and mobile updates.

## Versioning

- Keep `VERSION`, SQL schema, manifest schema, builder output, validation, and reader assumptions aligned.
- Additive optional fields may remain compatible only when old readers can safely ignore them.
- Removing/renaming required fields, changing stored text semantics, hint/vector identity, or required compatibility semantics requires a new format version.
- Never reuse a version number for an incompatible schema.

## Text integrity

`passage_text.text` is approved display text for a concrete text version and length variant. Generated hints belong only in `semantic_hint`. Machine translations are allowed only under an explicitly identified `machine_translation` text version.

## Validation

```bash
python tools/validate_schema.py
```

See [`IMPLEMENTATION.md`](IMPLEMENTATION.md) for current writer/reader mapping and root `docs/CORPUS_FORMAT.md` / `docs/TESTS.md` for semantics and validation expectations.
