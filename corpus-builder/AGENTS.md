# Corpus builder development rules

Root `AGENTS.md` and [`../corpus-core/AGENTS.md`](../corpus-core/AGENTS.md) also apply when shared contracts are involved.

## Package shape

Keep `sibyl_corpus_builder/` root intentionally small:

```text
__init__.py
cli.py
sources/
build/
curation/
translation/
```

Do not add new top-level implementation modules without a strong cross-feature orchestration reason. Prefer placing behavior in the owning feature.

### Feature boundaries

- `sources` owns external catalog/source acquisition through deterministic prepared canonical source output.
- `build` owns the automatic splitter, semantic hints, embeddings, runtime corpus writing/validation, and runtime model bundle.
- `curation` owns guided-question bundle export and large-LLM proposal import/exact-text validation.
- `translation` owns build-time large-LLM translation bundles/proposals for already validated curated passages; generated target text remains local data and must never be presented as source text.
- `corpus-core` owns only feature-neutral contracts/primitives shared by multiple features.

Each feature should expose intended callers through `api.py`. `command.py` translates argparse values to the public API. Implementation-private helpers belong under that feature's `_internal/` package.

A feature must not import another feature's `_internal` package. Root `cli.py` must not import `_internal` or source adapters directly. Architecture tests enforce these directions.

### `_internal` versus `corpus-core`

Use `_internal` when code is reusable **inside one feature** but still understands that feature's concepts. Use `corpus-core` only when the same contract/primitive makes sense independently of source acquisition, automatic build, LLM curation, and curated-passage translation.

Do not use either location as a miscellaneous utility bucket.

### Source adapters

Group source-specific behavior by source family:

```text
sources/adapters/libru/
    discovery.py
    fetch.py
    normalize.py

sources/adapters/gutenberg/
    fetch.py
    normalize.py
```

Cross-source document formats such as FB2 belong under `sources/adapters/formats/`. Add a new source family through one adapter package plus the explicit dispatch mapping in `sources/_internal/adapters.py`.

## Pipeline invariants

- Importing the package must not download sources/models, call remote APIs, or modify data.
- Every acquisition/build input must be explicit through source path/registry/configuration. Candidate registry sources require an explicit local-review override.
- Discovery manifests are editable developer review artifacts. `discover` must not write registry records, acquire texts, or change approval state.
- Batch acquisition from a selection processes only entries explicitly marked `decision = "include"`; per-work failures must be isolated and reported after the batch.
- Preserve literary text except for versioned, tested non-literary wrapper/newline normalization. Canonical text changes require a normalizer version change.
- Detect natural boundaries; never publish arbitrary mid-character truncations.
- Retain raw/canonical SHA-256 metadata and exact canonical-text source locators so every passage is reproducible.
- Build into staging output and publish only after validation succeeds.
- Persist completed embedding batches outside published output so interrupted real-text builds can resume. Cache identity must include embedding configuration and exact input text hashes.
- Production source provenance/rights metadata is mandatory.

## Build-time machine translation

- Translate only from already validated curated source passages in the first implementation slice.
- Preserve the original canonical passage unchanged; generated text is a separate `machine_translation` text version.
- Translation bundles/proposals with generated literary text stay under ignored `corpus-builder/data/` and must not be committed.
- Import/revalidation must pin source curation identity, passage IDs, exact source hashes, target language, provider/model, prompt version, and derived translation hashes.
- Local validation proves identity/completeness/provenance, not literary translation quality; human review may still reject a generated translation before publication.
- Runtime code must never call a translation service.

## Large-LLM curation

- `export-curation-bundle` starts from prepared canonical source text, before the automatic splitter.
- The external LLM may choose semantic relevance and natural boundaries, but it is never authoritative for literary wording.
- Import/revalidation must resolve each locator against local canonical text and verify canonical/text SHA-256 values.
- Export bundles may contain full canonical texts only under ignored local `corpus-builder/data/`; committed curation files contain locators/hashes/question mappings instead of copied books/passages.
- Export requires approved rights metadata unless a developer uses the explicit override after separately confirming external-service upload rights.

## Module documentation

Every Python package in the builder hierarchy, including `_internal` and source-adapter packages, must have a meaningful but compact `__init__.py` package docstring. Usually one or two short paragraphs should state the package responsibility and its most important ownership/dependency boundary. Do not repeat full pipeline diagrams, command workflows, or detailed module inventories already owned by `IMPLEMENTATION.md`/`WORKFLOW.md`.

For non-obvious modules/classes/orchestration methods, documentation must explain **where the code sits in the end-to-end pipeline**, what responsibility it owns, and what adjacent responsibilities it intentionally does not own. Source normalizers, fallback acquisition, preparation, embedding orchestration, publication, and curation validation require this context.

Avoid comments that merely restate individual statements.

## Tests

Use synthetic fixtures and no implicit network/model access.

```bash
make test-corpus-core
make test-corpus-builder
```

Add focused tests when moving behavior. Keep `test_architecture.py` aligned with dependency/package-documentation rules and `test_repository_hygiene.py` aligned with Git/archive protections for architectural source packages.

Concrete builder modules and call paths live in [`IMPLEMENTATION.md`](IMPLEMENTATION.md). Operational sequencing starts in [`../docs/WORKFLOW.md`](../docs/WORKFLOW.md).
