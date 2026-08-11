# Corpus builder development rules

Root `AGENTS.md` also applies.

## Pipeline invariants

- Importing the package must not download sources/models, call remote APIs, or modify data.
- Every build input must be explicit through source path/registry/configuration.
- Preserve approved literary text except for documented non-literary wrapper/newline normalization.
- Detect natural boundaries; never publish arbitrary mid-character truncations.
- Retain enough source-location/provenance metadata to reproduce each passage.
- Build into staging output and publish only after validation succeeds.
- Production source provenance/rights metadata is mandatory.

## Generated metadata

Semantic hints, summaries, quality scores, and embeddings are internal retrieval metadata. They are never literary quotations.

## Adapters

- `HintGenerator` owns internal semantic descriptions.
- `EmbeddingProvider` owns vector generation.
- Future source fetch, LLM, translation, and production embedding adapters must be explicit CLI/config choices.
- Keep deterministic local adapters for default tests.

## Tests

Use `pytest` with synthetic fixtures. Cover splitter boundaries, configuration validation, deterministic IDs, database/manifest population, staging/publication behavior, and contract validation.

```bash
PYTHONPATH=src python -m pytest
```

Detailed policies live in root `docs/ARCHITECTURE.md`, `docs/CONFIGURATION.md`, `docs/SOURCES.md`, `docs/CORPUS_FORMAT.md`, and `docs/TESTS.md`.
