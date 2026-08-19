# Sibyl implementation guide

## Purpose

This document maps Sibyl's stable architecture to the **current repository implementation**. It identifies the active cross-project call paths and concrete technology choices without duplicating subproject internals.

- [`CONCEPT.md`](CONCEPT.md) owns product intent and behavior.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) owns stable boundaries and responsibilities.
- This document owns the current cross-project realization.
- Subproject `IMPLEMENTATION.md` files own detailed classes, modules, and local call paths.

## Repository implementation map

| Area | Current responsibility | Detailed implementation |
|---|---|---|
| `mobile/` | Shared Kotlin runtime/UI plus Android and JVM Desktop hosts | [`../mobile/IMPLEMENTATION.md`](../mobile/IMPLEMENTATION.md) |
| `corpus-core/` | Feature-neutral canonical-source contracts, hashes, locators, atomic publication | [`../corpus-core/IMPLEMENTATION.md`](../corpus-core/IMPLEMENTATION.md) |
| `corpus-builder/` | Source ingestion, automatic corpus build, and large-LLM curation tooling | [`../corpus-builder/IMPLEMENTATION.md`](../corpus-builder/IMPLEMENTATION.md) |
| `corpus-format/` | Versioned SQLite/manifest persistence contract | [`../corpus-format/IMPLEMENTATION.md`](../corpus-format/IMPLEMENTATION.md) |
| `corpus-sources/` | Source/provenance/rights registry | [`../corpus-sources/IMPLEMENTATION.md`](../corpus-sources/IMPLEMENTATION.md) |
| `corpus-curation/` | Stable guided-question catalog and Git-safe curation metadata | [`../corpus-curation/README.md`](../corpus-curation/README.md) |
| `test-corpus/` | Synthetic deterministic build fixtures | [`../test-corpus/IMPLEMENTATION.md`](../test-corpus/IMPLEMENTATION.md) |

## Build-time wiring

```mermaid
flowchart TD
    U[External source / registry] --> S[sibyl_corpus_builder.sources]
    S --> P[Prepared canonical SourceDocument values]
    P --> B[sibyl_corpus_builder.build]
    P --> C[sibyl_corpus_builder.curation]
    C --> M[Validated curated exact ranges]
    M --> B
    B --> R[format-v4 corpus.db + vectors.json + manifest.json]
```

`sibyl_corpus_builder.cli` is only the command composition root. `sources` owns discovery, acquisition, normalization, and prepared-source publication. `curation` exports canonical texts plus the stable guided-question catalog, validates external LLM locator/hash proposals locally, and exposes validated exact slices through its public API. `build` owns mechanical free-form passage extraction/embeddings plus materialization of those validated curated slices and mappings into format-v4 runtime artifacts.

The shared `sibyl_corpus_core` package owns only feature-neutral prepared-source contracts and deterministic primitives. It does not own source adapters, embeddings, curation proposal semantics, or persisted runtime corpus format.

The current automatic real-text build uses `intfloat/multilingual-e5-small`. Exact passage text is indexed as retrieval text for the first real-corpus milestone; completed embeddings are cached beside prepared sources so interrupted builds can resume. The normal local assembly discovers all prepared source sets beneath the work root and compatible curated metadata, then atomically replaces one current runtime corpus while reusing those caches. LLM curation is independent of the automatic splitter: the external model chooses literary relevance and natural ranges, while local Python remains authoritative for exact canonical text, locators, and hashes.

## Runtime wiring

```mermaid
flowchart TD
    UI[SibylApp] --> FR[LocalRetrievalService]
    UI --> GR[LocalGuidedRetrievalService]
    FR --> E[EmbeddingEngine]
    FR --> I[VectorIndex]
    FR --> C[CorpusRepository]
    GR --> G[GuidedCorpusRepository]
    C --> SQ[SqliteCorpusRepository]
    G --> SQ
    E --> OE[OnnxE5EmbeddingEngine]
    I --> JV[JsonBruteForceVectorIndex]
    UI --> S[SelectionEngine]
```

Shared Kotlin keeps free-form and guided lookup as separate contracts. `LocalRetrievalService` embeds own-question text, retrieves a broader vector pool, hydrates stored passages, and deduplicates by passage ID. `LocalGuidedRetrievalService` accepts stable question IDs and reads curated candidates from a `GuidedCorpusRepository`; it has no embedding/vector dependency. Both return candidate pools and delegate final controlled-random choice to `SelectionEngine`.

The Desktop development host uses one read-only `SqliteCorpusRepository` for both corpus hydration paths. Format-v4 guided lookup reads only persisted `guided_question*` tables and exact `passage_text`; free-form lookup continues to use ONNX E5 plus `vectors.json`. Format v3 remains readable for free-form development corpora, while guided mode is unavailable.

`SibylApp` exposes a guided-question selector only when the runtime reports at least one mapped question, otherwise the existing free-form input remains the only mode. “Another passage” repeats the same retrieval mode/prompt and runs `SelectionEngine` again.

## Runtime artifacts and compatibility

A development corpus publishes:

```text
corpus.db
vectors.json
manifest.json
```

The Desktop embedding bundle is separate and contains the ONNX model, tokenizer data, and `model-manifest.json`. Corpus and model manifests are compared before retrieval so supported format version (v3/v4), model identity, vector dimensions, normalization, E5 query-prefix, and pooling assumptions cannot drift silently. V4 manifest counts also expose guided-question/mapping diagnostics; v3 readers default those counts to zero.

Generated corpus/model data remains under ignored `corpus-builder/data/` paths and is not committed or included in shareable archives.

## Current technology choices

| Scope | Current implementation |
|---|---|
| Shared application | Kotlin Multiplatform, Compose Multiplatform, coroutines |
| Desktop local inference | ONNX Runtime JVM + DJL Hugging Face Tokenizers |
| Desktop corpus access | Xerial SQLite JDBC + JSON vector loading |
| Current vector search | Exhaustive cosine search behind `VectorIndex` |
| Build-time ML | Sentence Transformers/PyTorch/NumPy in the optional `ml` extra |
| Core build tooling | Python standard library plus `corpus-core` contracts |

Host-specific setup and native-library workarounds belong in [`INSTALLATION.md`](INSTALLATION.md), not in this implementation overview.

## Temporary implementations versus stable boundaries

Several current choices are intentionally replaceable:

- `JsonBruteForceVectorIndex` is suitable for small development corpora and can later be replaced by ANN behind `VectorIndex`.
- Desktop uses SQLite JDBC directly; Android can provide a platform storage adapter behind shared contracts.
- Android still uses `DemoRetrievalService`; real Android embedding/index/storage adapters are not wired yet.
- richer generated semantic hints remain an optional build-time enhancement rather than a runtime requirement.

These are implementation choices, not architectural changes.

## Documentation maintenance

Update the document that owns the changed fact:

- product intent → `CONCEPT.md`;
- stable boundary/contract → `ARCHITECTURE.md`;
- cross-project current wiring → this file;
- detailed module/class wiring → the relevant subproject `IMPLEMENTATION.md`;
- operational sequence → `WORKFLOW.md`;
- command syntax/options → `USAGE.md`;
- setup/toolchain details → `INSTALLATION.md`.
