# Corpus builder implementation

## Scope and entry point

`corpus-builder/` is the build-time Python application that composes three explicit features around the shared contracts in [`../corpus-core/`](../corpus-core/):

```mermaid
flowchart TD
    CLI[sibyl_corpus_builder.cli] --> S[sources]
    CLI --> B[build]
    CLI --> C[curation]
    S --> P[Prepared canonical sources]
    P --> B
    P --> C
    B --> R[Automatic runtime corpus]
    C --> M[Validated curated metadata]
```

The package root intentionally contains only:

```text
sibyl_corpus_builder/
  __init__.py
  cli.py
  sources/
  build/
  curation/
```

`cli.py` is the composition root. It registers feature-owned command adapters and dispatches a parsed command to exactly one feature. It does not know source-site parsing, passage splitting, embeddings, SQLite details, or LLM proposal structure.

## Dependency rules

The implementation follows these boundaries:

```mermaid
flowchart TD
    CLI[cli.py] --> CMD[feature command.py]
    CMD --> API[feature api.py]
    API --> INT[feature _internal]
    INT --> CORE[corpus-core]
    ADP[source adapters] --> CORE
```

- feature callers use `api.py`, not another feature's `_internal` package;
- `_internal` means implementation-private to one feature, not a generic dumping ground;
- source-specific behavior lives under `sources/adapters/<source>/`;
- feature-neutral shared code belongs in `corpus-core`, not `_internal`;
- architecture regression tests enforce the most important import directions.

## `sources`: external artifacts to prepared canonical sources

Public surface: `sibyl_corpus_builder.sources.api`.

```mermaid
flowchart TD
    U[Catalog URL / registry record] --> D[Discover / resolve]
    D --> V[Developer review]
    V --> A[Acquire or import]
    A --> N[Source-specific normalization]
    N --> C[Raw + canonical artifact cache]
    C --> P[Prepare canonical source set]
    P --> O[corpus-core SourceDocument boundary]
```

### Command and API files

- `sources/command.py` — argparse definitions and user-facing result output for source commands;
- `sources/api.py` — public feature facade;
- `sources/models.py` — public `SelectionManifest` / `SelectionWork` review contracts.

### Source adapters

Adapters are grouped by **source**, so all code needed to understand one source family is close together:

```text
sources/adapters/
  libru/
    discovery.py
    fetch.py
    normalize.py
  gutenberg/
    fetch.py
    normalize.py
  formats/
    fb2.py
```

`libru/discovery.py` parses an author catalog and classifies entries into conservative `include` / `review` / `exclude` decisions. It does not acquire work bodies.

`libru/fetch.py` owns Lib.ru work-page artifact discovery and the resilient `TXT -> HTML -> FB2` fallback order.

`libru/normalize.py` owns Lib.ru-specific decoding/body-boundary/site-chrome logic. It preserves literary wording and keeps normalizer versions stable because exact canonical hashes and character locators depend on its output.

`gutenberg/fetch.py` locates/downloads a preferred UTF-8 plain-text artifact. `gutenberg/normalize.py` removes only the standard Project Gutenberg START/END transport wrapper.

`formats/fb2.py` is source-neutral FB2 parsing because FB2 is a document format rather than a source family.

### Source feature internals

- `_internal/adapters.py` — the single explicit mapping from source family to concrete discovery/fetch/normalization adapters;
- `_internal/http.py` — explicit build-time HTTP primitive used only by source adapters;
- `_internal/selection.py` — editable `selection.toml` persistence and validation;
- `_internal/registry.py` — typed access to permanent `corpus-sources` records and approval checks;
- `_internal/artifacts.py` — raw/canonical cache with hashes and normalizer identity;
- `_internal/acquisition.py` — candidate fallback/per-work isolation and registry/selection acquisition orchestration;
- `_internal/reports.py` — deterministic acquisition reports;
- `_internal/preparation.py` — the final source-ingestion stage that materializes deterministic canonical input shared by build and curation;
- `_internal/registration.py` — converts reviewed acquired Lib.ru selection items into disabled candidate registry records.

The important handoff is the prepared directory under `data/work/<name>/`. `corpus-core.prepared_sources.load_prepared_sources()` reads that directory; neither `build` nor `curation` reaches back into source `_internal` implementation.

## `build`: automatic passages and current generic runtime corpus

Public surface: `sibyl_corpus_builder.build.api`.

```mermaid
flowchart TD
    P[Prepared SourceDocument values] --> S[Automatic splitter]
    S --> H[Semantic hints]
    H --> E[Embeddings + resumable cache]
    E --> D[corpus.db]
    E --> V[vectors.json]
    D --> M[manifest.json]
    V --> M
    M --> Q[Validate]
    Q --> A[Atomic publish]
```

This remains the fallback/open-ended path for arbitrary user questions. It is intentionally mechanical and independent of large-LLM curation.

### Main files

- `build/command.py` — CLI adapter for `inspect-passages`, `build`, `validate`, and runtime-model download;
- `build/api.py` — high-level automatic pipeline. Reading this file should show the processing order without requiring knowledge of implementation details;
- `build/config.py` — immutable build configuration models and eager validation.

### Build internals

- `_internal/splitter.py` — paragraph/sentence-aware exact automatic ranges with deterministic IDs;
- `_internal/hints.py` — deterministic or exact-passage retrieval text;
- `_internal/embeddings.py` — hash fixture provider and opt-in Sentence Transformers provider;
- `_internal/embedding_pipeline.py` — provider selection, cache fingerprints, batching, progress, and cache reuse;
- `_internal/embedding_cache.py` — SQLite cache of completed embedding inputs;
- `_internal/database.py` — runtime SQLite writer; its `SCHEMA` must remain aligned with `corpus-format/schema.sql`;
- `_internal/manifest.py` — runtime artifact/embedding compatibility manifest;
- `_internal/validation.py` — final persisted database checks before publication;
- `_internal/runtime_model/specs.py` / `download.py` — explicit recipes and download/publish logic for the Desktop ONNX/tokenizer bundle.

The automatic splitter is not considered a literary curator. Its module documentation explicitly identifies it as a mechanical fallback used for generic retrieval.

## `curation`: external large-LLM passage selection

Public surface: `sibyl_corpus_builder.curation.api`.

```mermaid
flowchart TD
    P[Prepared canonical sources] --> E[Export bundle]
    Q[Stable guided questions] --> E
    E --> L[External large LLM]
    L --> R[Proposal locator/hash metadata]
    R --> V[Local exact-text validation]
    V --> G[Git-safe curated metadata]
```

### Main files

- `curation/command.py` — CLI adapter for export/import/validate commands;
- `curation/api.py` — public feature facade and workflow contract;
- `curation/models.py` — public guided-question catalog models.

### Curation internals

- `_internal/questions.py` — guided-question catalog loading/ID validation;
- `_internal/bundle.py` — deterministic ZIP export containing pinned canonical texts and questions;
- `_internal/proposal.py` — proposal import and normalized curated-mapping revalidation;
- `_internal/validation.py` — the trust boundary that resolves local canonical slices and verifies hashes/question links.

The external LLM decides literary relevance and natural boundaries. Local Python remains authoritative for exact text identity. Git-tracked curated metadata stores locators/hashes/matches rather than copied literary passages.

## `corpus-core` relationship

The builder depends on the separate local distribution `sibyl-corpus-core`. Shared code is intentionally small:

- `SourceDocument` and prepared-source loading;
- exact hashing;
- exact character locator parsing/slicing;
- newline/word-count primitives;
- atomic directory publication.

See [`../corpus-core/IMPLEMENTATION.md`](../corpus-core/IMPLEMENTATION.md). `corpus-core` must never import `corpus-builder`.

## Setup and validation

Install both local Python distributions from the repository root:

```bash
python -m pip install -e ./corpus-core -e './corpus-builder[dev]'
```

Focused validation:

```bash
make test-corpus-core
make test-corpus-builder
make check
```

`test_architecture.py` protects package dependency direction and requires meaningful package-level documentation in every `__init__.py`. `test_repository_hygiene.py` protects the refactored source layout from broad Git/archive exclusions, especially the architectural `sibyl_corpus_builder/build/` package.

## Generated directories

All paths under `corpus-builder/data/` are local/generated and ignored by Git and shareable archives. They may contain downloaded source artifacts, canonical/prepared texts, embedding caches, LLM curation bundles, runtime models, and published development corpora.

Use [`../docs/WORKFLOW.md`](../docs/WORKFLOW.md) for the operational start/continue flow and [`README.md`](README.md) / [`../docs/USAGE.md`](../docs/USAGE.md) for command details.
