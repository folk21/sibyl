# Changelog

This document records meaningful Sibyl product, architecture, data-contract, and capability evolution. Routine implementation, tooling, documentation, testing, CI, and repository-maintenance work belongs in [`WORKLOG.md`](WORKLOG.md).

## Unreleased

### Guided questions and literary curation

- added the first Desktop guided-question runtime: format-v4 persisted catalog/mappings, exact curated passage materialization, local SQLite guided lookup, and a shared guided/free-form selector using the existing controlled-random `SelectionEngine`;
- added a stable Russian guided-question catalog while preserving free-form local retrieval;
- added build-time large-LLM literary curation with deterministic bundle export, proposal import, and local exact-text/hash validation;
- kept curated guided retrieval conceptually separate from the automatic splitter/E5 path so arbitrary user questions can continue to use local semantic retrieval;
- expanded the guided catalog to 66 prompts, including work, books, health, illness, envy, hatred, identity, loss of meaning, nature, and responsibility to future generations.

### Source ingestion and corpus preparation

- added build-time large-LLM translation of validated curated foreign-language passages, with deterministic source bundles, strict source/hash/provenance import, local generated-text storage, and runtime materialization as labelled machine translations;
- added author-centric Lib.ru discovery with editable selection, resilient TXT -> HTML -> FB2 acquisition, deterministic canonical preparation, and optional source registration;
- added Project Gutenberg acquisition and reviewed local-file import paths;
- introduced reusable prepared canonical-source artifacts shared by automatic corpus builds and LLM curation;
- added exact automatic passage extraction with reproducible character locators and resumable embedding caching for real-text builds;
- added incremental all-available runtime corpus assembly: independently prepared authors are auto-discovered from the local work root, compatible curated metadata is included automatically, and existing embedding caches are reused without maintaining a separate aggregate prepared corpus.

### Local semantic retrieval

- added parallel original + preferred-language translation display for stored passage variants, with explicit machine-translation labelling and no runtime translation calls;
- added real JVM Desktop retrieval from generated corpus artifacts using local ONNX query embeddings, cosine candidate retrieval, exact SQLite passage resolution, and shared controlled-random selection;
- adopted `intfloat/multilingual-e5-small` for the current real-corpus path and persisted asymmetric E5 `passage: ` / `query: ` compatibility;
- added an explicit local runtime-model bundle for Desktop ONNX/tokenizer inference.

### Architecture and persisted contracts

- advanced the corpus format to v4 with guided-question catalog and question-to-passage mapping semantics while retaining Desktop v3 free-form read compatibility during migration;
- advanced the corpus format to v3 with exact source locators plus raw-artifact and canonical-text SHA-256 provenance;
- introduced `corpus-core` as the feature-neutral Python boundary for canonical source documents, exact hashing/locators, prepared-source loading, and atomic publication;
- separated `corpus-builder` into explicit `sources`, `build`, and `curation` feature boundaries;
- strengthened source approval/provenance rules so production text versions require pinned concrete artifacts and reviewed rights metadata.

## 0.1.0 - 2026-08-10

- created the initial Sibyl monorepo with the Android-first KMP application, shared passage-selection flow, Python corpus tooling, versioned corpus schema, and synthetic test corpus;
- established the core extractive-answer architecture: local semantic retrieval, multiple candidates, controlled-random selection, exact stored passages, and no required backend.
