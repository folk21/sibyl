# Changelog

## Unreleased

### Added

- 40 disabled/candidate source records and three seed source collections;
- source-registry validation with no third-party parser dependency;
- root `docs/TESTS.md`, `docs/SOURCES.md`, and `docs/CORPUS_FORMAT.md`;
- onboarding/start map in the root README;
- prioritized roadmap with `todo` / `in_progress` / `done` status;
- Mermaid diagrams for architecture and workflow diagrams;
- `make check-all`, `make validate-sources`, and `make smoke-corpus` targets;
- JVM Compose Desktop development harness with `make run-desktop`;
- desktop JVM shared-test target (`make test-desktop`).

### Changed

- active application development targets are Android plus JVM Desktop; `make test-mobile` runs Android host tests and `make test-desktop` runs shared JVM tests;
- iOS/Kotlin Native targets are deferred and removed from the active Gradle configuration until iOS development resumes;
- detailed documentation is consolidated under root `docs/`;
- subprojects keep only local `README.md` and `AGENTS.md` documentation entry points;
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
