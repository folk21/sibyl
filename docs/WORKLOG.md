# Worklog

This is the detailed engineering and maintenance history of Sibyl. It intentionally includes implementation, tooling, test, documentation, CI, and repository-hygiene work that is too detailed for the normal project context.

For the concise history of meaningful product, architecture, data-contract, and capability evolution, see [`CHANGELOG.md`](CHANGELOG.md). This file is not required reading for normal implementation work; consult it when the history of a specific decision or maintenance change is relevant.

## 2026-08-18 — Introduce active change specifications

- added `docs/specs/` as a lightweight change-spec layer for significant planned/in-progress work without creating a second canonical description of the current system;
- defined active/archive lifecycle, requirement/scenario traceability, and the rule that accepted changes update owning current-state docs before their spec is archived;
- added the first active spec for the guided-question runtime vertical slice spanning corpus format, builder assembly, shared retrieval contracts, Desktop runtime/UI, and tests;
- kept active specs in normal LLM snapshots while excluding archived specs alongside the detailed worklog.

## 2026-08-18 — Approved-only LLM curation export

- added `--approved-only` to `export-curation-bundle` so mixed prepared source sets can skip versions whose rights metadata is not `approved`;
- kept the default export mode strict and retained `--allow-unapproved` as an explicit reviewed development override;
- made `--approved-only` and `--allow-unapproved` mutually exclusive in both the CLI and Python API, with an explicit error when approved-only filtering leaves no sources;
- added focused tests for filtering, empty approved-only exports, and conflicting rights modes.

## 2026-08-18 — Separate project evolution from detailed engineering history

- preserved the previous detailed changelog as this worklog;
- reduced `CHANGELOG.md` to meaningful product, architecture, data-contract, and capability evolution;
- documented the distinction in the root README and repository instructions;
- excluded `docs/WORKLOG.md` from normal concatenated LLM snapshots while keeping it in Git and full repository archives.

## 2026-08-17 — Streamline documentation ownership and model context

- removed `docs/DEVELOPMENT.md` because repository change rules are already owned by root/local `AGENTS.md`;
- made `WORKFLOW.md` the single end-to-end operational path, `USAGE.md` the command/option reference, and `SOURCES.md` the source/provenance policy owner;
- reduced repeated command sequences and volatile derived counts across root/subproject documentation while preserving useful local invariants and navigation;
- shortened root implementation guidance and Python package docstrings so they provide local architectural context without repeating detailed implementation documents;
- linked the root README product summary directly to `docs/CONCEPT.md`.


## 2026-08-17 — Align Git, CI, and documentation with the Python corpus refactor

- narrowed `.gitignore` build-output rules so Git can track the architectural `sibyl_corpus_builder/build/` source package while still excluding known generated build directories;
- changed corpus-builder CI to run the repository-owned `make check` contract and to trigger on root hygiene scripts, `.gitignore`, `Makefile`, and source-registry changes covered by that contract;
- documented package-docstring and repository-hygiene regression coverage and clarified that `corpus-core` does not automatically change with every persisted runtime-format revision;
- added a regression test preventing broad `**/build/` Git ignore rules from returning.


## 2026-08-17 — Preserve Python `build` source feature in repository artifacts

- fixed `archive.sh` and `concat_sibyl.sh` so generated build-output exclusions no longer match `corpus-builder/src/sibyl_corpus_builder/build/`;
- added output validation to both helpers so a shareable archive/snapshot fails instead of silently omitting the automatic-build feature;
- added regression tests covering the source-package/archive-hygiene boundary.


## Unreleased

### Added

- `corpus-core/` as a separate feature-neutral Python subproject owning `SourceDocument`, prepared-source loading, exact hashing/character locators, shared text primitives, and atomic directory publication;
- Python architecture regression tests that prevent `corpus-core -> corpus-builder`, root CLI access to feature internals, and cross-feature `_internal` dependencies;
- source adapters grouped by source family (`sources/adapters/libru`, `sources/adapters/gutenberg`) plus a source-neutral FB2 format adapter;
- `docs/WORKFLOW.md` as the primary start/continue guide across source preparation, large-LLM curation, generic corpus builds, and Desktop runtime;
- `corpus-curation/questions.json` with 66 stable Russian guided questions/states plus local rules for Git-safe LLM curation metadata;
- `export-curation-bundle`, `import-curation`, and `validate-curation` builder commands for deterministic external-LLM handoff and exact canonical locator/hash verification without committing copied passage text;
- focused curation tests covering the 66-item catalog, reproducible export bundles, exact-slice import, and hash mismatch rejection;
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

- every Python package now has a meaningful `__init__.py` package docstring describing its pipeline position, responsibilities, and dependency/ownership boundaries; architecture tests reject missing or placeholder package documentation;
- refactored `sibyl_corpus_builder` from a flat module set into three explicit features: `sources`, `build`, and `curation`; the package root now contains only `__init__.py`, `cli.py`, and feature packages;
- root `cli.py` is now a thin composition entry point, while each feature owns its `command.py`, public `api.py`, and implementation-private `_internal` modules;
- source acquisition/normalization/preparation and automatic build modules now include pipeline-position documentation explaining how each non-obvious stage fits the end-to-end workflow;
- Python setup/CI/Make targets now install/test both local `corpus-core` and `corpus-builder` distributions;
- repository documentation rules now prefer vertical Mermaid flowcharts for sequential pipelines longer than four major blocks, while relationship maps and sequence diagrams keep the layout that best communicates structure;
- Kotlin documentation now requires meaningful KDoc for every type and more detailed responsibility/algorithm/invariant/resource-lifecycle notes for non-obvious retrieval, selection, inference, persistence, and compatibility code;
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
