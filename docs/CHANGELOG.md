# Changelog

## Unreleased

### Added

- `docs/CONCEPT.md` for the product idea/user promise and root/subproject `IMPLEMENTATION.md` guides for the current technical realization;
- concise KDoc/docstrings for production classes and the main orchestration/validation methods across Kotlin and Python code;
- real Desktop retrieval from generated `manifest.json` + `corpus.db` + `vectors.json`, using local ONNX query embeddings, brute-force cosine search, and shared controlled-random selection;
- explicit E5 `query_prefix` persisted alongside `passage_prefix` and validated at runtime;
- `download-runtime-model` command for the ignored local `multilingual-e5-small` ONNX/tokenizer development bundle;

- Lib.ru/Классика author-page discovery into editable selection manifests with `include` / `exclude` / `review` decisions and default epistolary exclusion;
- batch `acquire`, `prepare-selection`, and optional `register` corpus-builder commands;
- Lib.ru TXT → HTML → FB2 acquisition fallback with versioned `libru_txt_v1`, `libru_html_v1`, and `libru_fb2_v1` normalization;
- selection/acquisition/normalization/registration tests with no network dependency, including malformed FB2 fallback and per-work batch failure isolation;
- explicit Project Gutenberg source acquisition and reviewed local-file import commands;
- local raw/canonical source artifact cache with SHA-256 verification;
- deterministic `prepare` and `inspect-passages` corpus-builder workflows;
- exact source-slice passage extraction with character locators and hard maximum size;
- opt-in Sentence Transformers embedding provider and first `multilingual-e5-small` evaluation config;
- 40 disabled/candidate source records and three seed source collections;
- source-registry validation with no third-party parser dependency;
- root `docs/TESTS.md`, `docs/SOURCES.md`, and `docs/CORPUS_FORMAT.md`;
- onboarding/start map in the root README;
- prioritized roadmap with `todo` / `in_progress` / `done` status;
- Mermaid diagrams for architecture and workflow diagrams;
- `make check-all`, `make validate-sources`, and `make smoke-corpus` targets;
- JVM Compose Desktop development harness with `make run-desktop`;
- desktop JVM shared-test target (`make test-desktop`);
- resumable embedding cache with per-batch checkpoints and visible build-stage/progress reporting;
- `concat_sibyl.sh` source-only project snapshot helper.

### Changed

- `archive.sh` and `.gitignore` now exclude all `corpus-builder/data/` downloads/prepared/output/cache content plus local ML/tool caches and generated project snapshots;
- pinned the optional corpus-builder ML stack to NumPy 1.26.4, PyTorch 2.2.2, and Sentence Transformers 3.4.1, with Python 3.11/3.12 documented for reproducible Intel macOS embedding builds;
- Lib.ru batch acquisition reports `acquired` / `failed` / `skipped` results and preserves successful cache entries when another work fails;
- source onboarding now supports catalog-first review before permanent registry creation, while discovery/acquisition never auto-approves sources;
- shareable archive handoff rules now distinguish `FULL` vs `PATCH`, preserve the `sibyl/` root, and require explicit deleted-file reporting;
- corpus format advanced to v3 to persist source locator, raw artifact SHA-256, and canonical text SHA-256 provenance;
- source registry approval now requires pinned raw/canonical checksums for enabled versions;
- active application development targets are Android plus JVM Desktop; `make test-mobile` runs Android host tests and `make test-desktop` runs shared JVM tests;
- iOS/Kotlin Native targets are deferred and removed from the active Gradle configuration until iOS development resumes;
- cross-project product/architecture/policy documentation remains under root `docs/`, while each subproject now has one focused `IMPLEMENTATION.md` beside its README/AGENTS;
- `docs/ARCHITECTURE.md` now focuses on stable boundaries, with concrete classes/libraries moved to implementation guides;
- source registry seed format is TOML so validation can use Python 3.11 `tomllib` without extra dependencies;
- shareable repository archives now use `sibyl/` as the top-level directory and exclude local Gradle/Python caches, local distributions, and `*.egg-info` metadata;
- removed the inactive iOS placeholder directory and obsolete Kotlin/Native disabled-target setting while iOS development remains deferred;
- mobile CI now uses explicit Android/Desktop test targets instead of `:shared:allTests`.

## 0.1.0 - 2026-08-10

### Added

- initial Sibyl monorepo layout;
- Android-first Kotlin Multiplatform mobile skeleton;
- shared demo passage-selection flow;
- Python corpus-builder skeleton;
- versioned corpus schema and validation tooling;
- synthetic test corpus;
- local privacy/content-provenance rules;
- corpus-builder contract regression test and staged artifact publication.

### Notes

The mobile runtime intentionally uses demo adapters rather than bundled production model/index assets. The architecture is prepared for ONNX Runtime and ANN adapters without making those dependencies prerequisites for the first checkout.
