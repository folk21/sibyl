# Corpus builder development rules

Root `AGENTS.md` also applies.

## Pipeline invariants

- Importing the package must not download sources/models, call remote APIs, or modify data.
- Every acquisition/build input must be explicit through source path/registry/configuration. Candidate registry sources require an explicit local-review override.
- Discovery manifests are editable developer review artifacts. `discover` must not write registry records, acquire texts, or change approval state.
- Batch acquisition from a selection processes only entries explicitly marked `decision = "include"`; `review` and `exclude` are never acquired implicitly. Per-work failures must be isolated and reported after the batch rather than aborting at the first bad artifact.
- Preserve literary text except for versioned, tested non-literary wrapper/newline normalization. Canonical text changes require a normalizer version change.
- Detect natural boundaries; never publish arbitrary mid-character truncations.
- Retain raw/canonical SHA-256 metadata and exact canonical-text source locators so every passage is reproducible.
- Build into staging output and publish only after validation succeeds.
- Persist completed embedding batches in a local cache outside published output so interrupted real-text builds can resume without recomputing successful batches. Cache identity must include embedding configuration and exact input text hashes.
- Production source provenance/rights metadata is mandatory.

## Generated metadata

Semantic hints, summaries, quality scores, and embeddings are internal retrieval metadata. They are never literary quotations.

## Adapters

- `HintGenerator` owns internal semantic descriptions.
- `EmbeddingProvider` owns vector generation.
- Source discovery/fetch, ML, LLM, translation, and production embedding adapters must be explicit CLI/config choices and never run on package import.
- Lib.ru acquisition prefers TXT, then work-page HTML, then FB2. Source-specific normalizers must remain versioned and tested; malformed/unsupported candidates must fall through without corrupting a successfully acquired batch.
- Keep deterministic local adapters for default tests.

## Tests

Use `pytest` with synthetic fixtures. Cover splitter boundaries, configuration validation, deterministic IDs, database/manifest population, staging/publication behavior, and contract validation.

```bash
PYTHONPATH=src python -m pytest
```

Detailed policies live in root `docs/ARCHITECTURE.md`, `docs/CONFIGURATION.md`, `docs/SOURCES.md`, `docs/CORPUS_FORMAT.md`, and `docs/TESTS.md`.
