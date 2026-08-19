# Roadmap

Statuses are repository state, not promises: `todo`, `in_progress`, `done`.

Priorities:

- `P0` — required for the first meaningful offline Android product slice;
- `P1` — important for MVP quality/release;
- `P2` — valuable after the core slice works;
- `P3` — optional/later exploration.

## Foundation and repository

| ID | Status | Priority | Work |
|---|---|---:|---|
| F-01 | done | P0 | Establish monorepo boundaries: `mobile`, `corpus-builder`, `corpus-format`, `corpus-sources`, `test-corpus`. |
| F-02 | done | P0 | Create Android-first KMP/Compose project with separate Android entry point. |
| F-03 | done | P0 | Define `EmbeddingEngine`, `VectorIndex`, and deterministic `SelectionEngine` boundaries. |
| F-04 | done | P0 | Add Python corpus-builder skeleton with staging and validation. |
| F-05 | done | P0 | Define corpus format v3 with work/text-version/passage/passage-text/hint separation plus source artifact/canonical hashes. |
| F-06 | done | P1 | Keep cross-project docs under root `docs/` and add focused subproject `IMPLEMENTATION.md` guides without local docs trees. |
| F-07 | done | P1 | Add root onboarding/test map and Mermaid architecture diagrams. |
| F-08 | done | P0 | Add JVM Compose Desktop development harness using the shared UI/runtime code. |
| F-09 | done | P0 | Wire Desktop to a built local corpus using ONNX query embeddings, brute-force development vector search, SQLite passage lookup, and the shared SelectionEngine. |
| F-10 | todo | P2 | Add an optional retrieval diagnostics CLI if low-level candidate/index inspection becomes cumbersome through the Desktop UI. |

## Sources and corpus ingestion

| ID | Status | Priority | Work |
|---|---|---:|---|
| S-01 | done | P0 | Define source registry concepts for provenance, rights, text role, category, and approval. |
| S-02 | done | P0 | Seed 40 candidate works across Russian classics, foreign originals, philosophy, and sacred texts. |
| S-03 | done | P0 | Add deterministic source-registry validation and collection-reference checks. |
| S-04 | in_progress | P0 | Review/pin concrete editions or digital revisions and rights metadata for the first usable source subset. |
| S-05 | in_progress | P0 | Support Russian Wikisource through reviewed local UTF-8 import + hashing; add safe automatic revision-aware extraction later. |
| S-06 | done | P0 | Implement explicit Project Gutenberg plain-text fetch adapter with versioned wrapper removal and exact-content preservation. |
| S-07 | done | P0 | Add local source artifact cache outside Git with raw/canonical SHA-256 metadata and prepared manifests. |
| S-07a | done | P0 | Add Lib.ru author-page discovery into editable `include` / `exclude` / `review` selection manifests, excluding correspondence by default. |
| S-07b | done | P0 | Add resilient batch Lib.ru acquisition with TXT → HTML → FB2 fallback, versioned normalizers, per-work failure reporting, batch preparation, and optional candidate registration with pinned hashes. |
| S-08 | todo | P1 | Add approved historical Russian human translations where preferable to machine translation. |
| S-09 | todo | P1 | Add build-time machine translation adapter for approved foreign originals; persist provider/model metadata. |
| S-10 | in_progress | P1 | Expand reviewed source registry beyond the seed 40 using catalog discovery + human review while keeping exact-version provenance. |
| S-11 | todo | P1 | Define sacred-text tradition/version metadata where the distinction matters to users. |

## Corpus quality and ML preparation

| ID | Status | Priority | Work |
|---|---|---:|---|
| C-01 | done | P0 | Add deterministic exact-source passage extraction using paragraph/sentence boundaries with hard max size and word-boundary fallback. |
| C-02 | todo | P0 | Produce explicit `short` / `standard` / `extended` variants without arbitrary truncation. |
| C-03 | in_progress | P0 | Evaluate `intfloat/multilingual-e5-small` as the first multilingual baseline; production model lock remains pending. |
| C-04 | done | P0 | Add opt-in Sentence Transformers embeddings with model metadata, batched progress reporting, and resumable per-input embedding cache. |
| C-05 | todo | P0 | Write a USearch/HNSW-compatible ANN artifact with stable semantic-hint IDs. |
| C-06 | todo | P1 | Add LLM-assisted semantic hints behind an explicit build-time adapter. |
| C-07 | todo | P1 | Add passage quality scoring: standalone quality, context dependency, spoiler risk, duplicate/near-duplicate detection. |
| C-08 | todo | P1 | Generate multiple semantic hints per passage to improve metaphorical/lateral retrieval. |
| C-09 | todo | P1 | Build a qualitative evaluation set of questions and expected plausible passage regions, not single gold answers. |
| C-10 | todo | P2 | Benchmark corpus/index size, build cost, and retrieval quality for 10k / 50k / 100k+ passage packages. |
| C-11 | done | P0 | Add the first large-LLM curation infrastructure: 66 stable guided prompts, deterministic canonical-text export bundles, Git-safe locator/hash proposals, and local exact-text import/validation. |
| C-12 | done | P0 | Publish curated guided-question mappings into the format-v4 runtime corpus and route guided question IDs to candidate pools while retaining `SelectionEngine` serendipity. |
| C-13 | done | P0 | Assemble one runtime corpus from all locally available independently prepared source sets, automatically include compatible curated metadata, and reuse compatible embedding caches. |

## Android retrieval slice

| ID | Status | Priority | Work |
|---|---|---:|---|
| A-01 | in_progress | P0 | Package the selected query embedding model; Desktop now uses a downloaded ONNX/tokenizer bundle, while Android packaging remains to be implemented. |
| A-02 | todo | P0 | Implement tokenizer + ONNX Runtime `EmbeddingEngine` on Android. |
| A-03 | todo | P0 | Implement USearch/HNSW `VectorIndex` Android adapter. |
| A-04 | todo | P0 | Load a real 500–2,000-passage approved development corpus on device. |
| A-05 | in_progress | P0 | Complete selection policy beyond current weights: candidate-pool sizing, recency, author/work diversity, semantic-cluster diversity. |
| A-06 | todo | P1 | Add close/lateral/strange sampling policy while retaining a minimum semantic-relevance gate. |
| A-07 | todo | P0 | Persist automatic history locally. |
| A-08 | todo | P0 | Persist saved encounters as explicit `question + passage (+ optional note)` records. |
| A-09 | todo | P1 | Add corpus-format/model/index compatibility checks before search. |
| A-10 | todo | P1 | Measure latency, memory, startup cost, and index size on representative Android devices. |

## Product MVP

| ID | Status | Priority | Work |
|---|---|---:|---|
| P-01 | in_progress | P0 | Question → passage experience with exact stored answer and controlled randomness. |
| P-02 | todo | P0 | Source-details reveal: author, work, chapter/location, text version, translator/provider. |
| P-03 | todo | P0 | History screen and saved-encounter screen backed by local persistence. |
| P-04 | todo | P1 | User response-length preference using prepared variants. |
| P-05 | todo | P1 | Library scope filters: any installed corpus, author/work, collection, and content category. |
| P-06 | todo | P1 | Sacred-text include/exclude preference using normal category filtering. |
| P-07 | todo | P1 | Display original + Russian translation when both exist; visibly label machine translation. |
| P-08 | todo | P1 | Graceful no-answer/fallback behavior when semantic relevance is too weak. |
| P-09 | todo | P1 | Local deletion controls for history/saved encounters and documented backup behavior. |
| P-10 | todo | P1 | Offline installable corpus packages with integrity verification. |
| P-11 | todo | P2 | Free core corpus (rough target 5k–10k strong passages) and larger paid corpus package(s), without requiring server-side question processing. |
| P-12 | todo | P2 | Store entitlement/download flow for paid corpus packages. |
| P-13 | done | P0 | Add Desktop guided-question/state selection backed by curated runtime mappings while preserving free-form user questions. |

## Literary interaction modes

| ID | Status | Priority | Work |
|---|---|---:|---|
| L-01 | todo | P2 | Chain-of-passages mode where each next exact fragment continues, contrasts, or reframes the current state. |
| L-02 | todo | P2 | “Another answer” behavior that preserves semantic plausibility while favoring a different author/work/cluster. |
| L-03 | todo | P2 | Contextual resurfacing of an old passage/encounter after a long interval without permanent repeat blacklists. |
| L-04 | todo | P3 | Multi-voice/literary-dialog mode composed only from exact stored passages, never synthetic character quotations. |

## iOS (deferred)

iOS development is intentionally out of scope for the current Android-first phase. No iOS Gradle targets are configured.

| ID | Status | Priority | Work |
|---|---|---:|---|
| I-01 | todo | P3 | Add production iOS application entry point. |
| I-02 | todo | P3 | Implement/bridge ONNX query embedding adapter. |
| I-03 | todo | P3 | Implement/bridge vector-index adapter. |
| I-04 | todo | P3 | Verify equivalent candidate retrieval/selection contracts across Android and iOS. |
| I-05 | todo | P3 | Adapt local storage, package installation, and platform privacy behavior. |

## Optional infrastructure

| ID | Status | Priority | Work |
|---|---|---:|---|
| O-01 | todo | P2 | Static CDN/object-storage distribution for signed/versioned corpus/model packages. |
| O-02 | todo | P3 | Optional private backup/sync of user history and encounters. |
| O-03 | todo | P3 | Evaluate whether any future feature truly requires an application backend. |

A backend is **not** a requirement for the core product. Question embedding, retrieval, selection, history, and saved encounters remain on-device unless a future architecture decision explicitly changes that boundary.
