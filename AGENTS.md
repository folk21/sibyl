# AGENTS.md

This file contains repository-wide development rules for Sibyl. Read the nearest local `AGENTS.md` before changing `mobile/`, `corpus-core/`, `corpus-builder/`, `corpus-curation/`, `corpus-format/`, `corpus-sources/`, or `test-corpus/`.

## Project summary

Sibyl is an offline-first literary discovery application. A user question is embedded locally, matched against semantic metadata for literary passages, and answered with an exact stored passage selected from a semantically plausible candidate pool using controlled randomness.

Primary scopes:

- `mobile/` — Kotlin Multiplatform runtime/UI with Android product and JVM Desktop development entry points;
- `corpus-core/` — feature-neutral Python canonical-source contracts and deterministic shared primitives;
- `corpus-builder/` — Python build-time source ingestion, automatic corpus build, and LLM-curation tooling;
- `corpus-format/` — versioned persisted contract;
- `corpus-sources/` — source/provenance/rights registry;
- `corpus-curation/` — guided-question catalog and validated LLM curation metadata;
- `test-corpus/` — synthetic fixtures.

There is no required backend in the core architecture.

## Language and documentation

- Write software code, comments, KDoc/docstrings, tests, config comments, examples, README/AGENTS files, and software documentation in English.
- Literary source text keeps its source language and exact approved wording.
- Avoid comments that restate code. Document useful contracts/invariants instead.
- Give every Kotlin class/interface/enum/data class a meaningful KDoc. For non-obvious runtime, retrieval, persistence, or algorithmic code, explain the responsibility, why the class exists, the main processing order, important invariants/assumptions, and notable fallback/resource-ownership behavior. Keep simple models concise and avoid line-by-line narration.
- Document substantial public/orchestration methods when their ordering, side effects, compatibility rules, or exact-text guarantees are not obvious from the signature alone.
- Every non-trivial Python package must have a meaningful, concise package-level docstring in `__init__.py`. Usually one or two short paragraphs are enough: state what the package owns and its most important dependency/ownership boundary. Do not repeat full pipeline diagrams, command instructions, or detailed module inventories that belong in `IMPLEMENTATION.md`.
- Cross-project product, architecture, policy, workflow, and compatibility documentation lives under root `docs/`.
- Each code subproject keeps `README.md` for local quick start, `AGENTS.md` for local change rules, and `IMPLEMENTATION.md` for concrete classes/files/libraries in that subproject.
- Do not create separate subproject `docs/` trees or duplicate root architecture/policy content in local implementation guides.
- Architecture/workflow diagrams should use Mermaid instead of ASCII/pseudo-text diagrams when a diagram is useful.
- Prefer vertical Mermaid flowcharts (`TD`/`TB`) for sequential pipelines with more than four major blocks. Short chains and relationship/component maps may remain horizontal (`LR`) when that is easier to read. `sequenceDiagram` is exempt because its layout communicates participants and call order differently.

## Core product invariants

- Primary answers are extractive: displayed literary text must exist verbatim in an approved stored text version.
- Never present generated hints, summaries, synthetic dialogue, or LLM output as quotations.
- Retrieval must return multiple plausible candidates; do not replace selection with top-1 nearest-neighbor lookup.
- Serendipity is required. Semantic relevance is a gate/weight, not the sole decision rule.
- Randomness must be injectable for deterministic tests.
- Repetition is allowed; recency may reduce probability but must not create a permanent blacklist by default.
- History is automatic. A saved encounter explicitly preserves the user question with the selected passage.
- Response length selects prepared variants; never truncate literary text arbitrarily.
- Original/human/machine translation and passage length are separate dimensions.
- Machine translations must be labelled in persisted metadata and UI.
- Sacred texts are a content category/filter, not a separate retrieval engine.

## Privacy and networking

- Keep question-to-passage processing local by default.
- Do not add telemetry, remote inference/search/history, mandatory accounts, or question logging without explicit approval.
- Optional network/model/translation adapters belong to explicit build-time or package-distribution flows, not implicit runtime behavior.
- Never expose API keys in mobile source or committed configuration.

## Content provenance and rights

- Treat copyright, translation rights, and digital-edition/source terms as explicit corpus metadata.
- `corpus-sources/` may contain disabled candidate records while review is incomplete.
- An enabled production source must pin a concrete edition/revision/artifact and have approved rights/provenance metadata.
- A public-domain original does not imply a modern translation is reusable.
- Do not commit large downloaded texts, scans, generated translations, production indexes, model files, or embedding caches. `corpus-builder/data/` is local/generated only; committed fixtures belong under `test-corpus/`.

## Architecture boundaries

- `mobile/` consumes published corpus artifacts through `corpus-format` and must not know how semantic hints were generated.
- `corpus-core/` is feature-neutral and must not depend on `corpus-builder/`, source adapters, LLM proposal formats, or runtime corpus writer internals.
- `corpus-builder/` may depend on `corpus-core` and format/source declarations but must not execute mobile code. Its Python root stays a thin CLI composition layer over `sources`, `build`, and `curation` features.
- `corpus-format/` owns persisted semantics and must not depend on builder/mobile internals.
- `corpus-sources/` owns source/version declarations and review state, not passage extraction or ranking.
- `corpus-curation/` owns stable guided-question IDs plus small LLM curation locator/hash metadata; it must not store downloaded canonical books or bypass local exact-text validation.
- Source discovery manifests are developer review artifacts: discovery may classify candidates but must never approve or publish them automatically.
- Platform-specific ONNX/index APIs stay behind small interfaces such as `EmbeddingEngine` and `VectorIndex`. The Desktop development harness may use JVM ONNX Runtime, SQLite JDBC, and brute-force vectors for small corpora; these dependencies must not leak into common code.
- The JVM Desktop app is a development harness: reuse shared UI/runtime code and do not introduce a REST/backend boundary just to run it locally.
- UI must not implement ranking, vector-search internals, or corpus parsing.
- Python features must not import another feature's `_internal` package. Source-specific discovery/fetch/normalization belongs under `corpus-builder/.../sources/adapters/<source>/`; shared feature-neutral primitives belong in `corpus-core`, not a generic utility bucket.

## Change workflow

1. Read root and nearest local `AGENTS.md`, then inspect the current code/tests and owning documentation for the affected scope.
2. For a significant cross-cutting, persisted-contract, or substantial P0/P1 change, read/create the relevant active change spec under `docs/specs/active/` before implementation. Small bug fixes and narrow maintenance work do not require a spec.
3. Make the smallest coherent change and preserve established terminology/boundaries.
4. Keep cross-project contracts synchronized: persisted format changes must be checked against builder writers/validators and mobile readers; source-registry changes must preserve provenance/rights rules.
5. Add or update focused tests and the single owning document for changed public behavior, commands, contracts, or architecture. Behavioral tests for a specced change should trace back to its requirements/scenarios.
6. Run focused validation first, then `make check` from the repository root where practical.
7. After a specced change is accepted, update current-state owning docs and move the completed spec to `docs/specs/archive/`.

## Testing

- Kotlin selection tests use deterministic injected randomness.
- Python tests use `pytest` with synthetic fixtures.
- Format tests validate schema/metadata/compatibility.
- Source registry validation must reject broken collection references and must enforce stricter rules for `enabled = true` records.
- Default tests require no model downloads, source downloads, network APIs, or GPU jobs.
- Behavior/contract changes require focused tests in the same change.

From the repository root:

```bash
make check
```

Use `make check-all` when the Android toolchain is available. Use `make run-desktop` for fast interactive development. See `docs/TESTS.md`.

## Documentation ownership

Use one owning root document and link to it instead of duplicating detailed content:

- root `README.md` — project overview, onboarding map, quick start, source-extension hint;
- `docs/WORKFLOW.md` — primary operational start/continue flow across source preparation, LLM curation, corpus build, and runtime;
- `docs/CONCEPT.md` — product purpose, user promise, invariants, and non-goals;
- `docs/ARCHITECTURE.md` — stable system boundaries and data flow;
- `docs/IMPLEMENTATION.md` — cross-project map of the current concrete implementation;
- `docs/INSTALLATION.md` — toolchains/setup;
- `docs/TESTS.md` — test matrix;
- `docs/USAGE.md` — command-oriented runtime/build reference;
- `docs/CONFIGURATION.md` — configuration ownership;
- `docs/SOURCES.md` — source/provenance/rights/normalization policy;
- `docs/CORPUS_FORMAT.md` — persisted format semantics/versioning/validation;
- `docs/SECURITY_AND_PRIVACY.md` — privacy/content-integrity rules;
- `docs/ROADMAP.md` — prioritized work with explicit status; detailed requirements for active work belong in change specs rather than roadmap rows;
- `docs/specs/README.md` — change-spec lifecycle/template; `docs/specs/active/` describes intended deltas for significant planned/in-progress work and is normal implementation context, while `docs/specs/archive/` is historical design intent;
- `docs/CHANGELOG.md` — concise history of meaningful product, architecture, data-contract, and capability evolution;
- `docs/WORKLOG.md` — detailed engineering/maintenance history; it is not required context for normal implementation work and should be consulted only when historical reasoning or a prior maintenance change is relevant;
- subproject `README.md` — local overview and commands;
- subproject `IMPLEMENTATION.md` — current modules/classes/libraries and concrete call paths;
- local `AGENTS.md` — protected rules close to code.

Documentation changes follow one ownership rule: operational start/continue flow belongs in `WORKFLOW.md`; command syntax/options belong in `USAGE.md`; source/provenance policy belongs in `SOURCES.md`; product meaning belongs in `CONCEPT.md`; stable boundaries belong in `ARCHITECTURE.md`; concrete code/library wiring belongs in `IMPLEMENTATION.md`. Root/local `AGENTS.md` own repository change rules. Active change specs describe intended future deltas and must not be treated as current-state documentation; after implementation, durable results move into the owning docs and the spec is archived. `CHANGELOG.md` records only meaningful project evolution; routine implementation and maintenance details belong in `WORKLOG.md`. Prefer links over repeated command sequences or volatile derived facts such as current catalog/registry counts.

## Repository archive checklist

1. Include no private user questions, real saved encounters, restricted texts, secrets, downloaded corpora, model files, generated production artifacts, caches, `.gradle`, `__pycache__`, or `.pytest_cache`.
2. Keep documented commands aligned with real targets/scripts.
3. Confirm corpus-format version metadata matches builder/mobile assumptions.
4. From the repository root, run `make check` and focused mobile tests where relevant.
5. Validate Markdown links and source-registry references.
6. Full generated archives must use `sibyl/` as the top-level directory.
7. Name complete repository archives with `FULL` and patch archives with `PATCH`. A patch archive contains only added/modified files under `sibyl/`; deleted paths must be reported explicitly because extracting a ZIP cannot delete them.
8. When handing off either a full archive or a patch, explicitly report the list of deleted files; write `none` when there are no deletions.
9. `archive.sh` and `concat_sibyl.sh` must exclude downloaded/generated corpus data, embedding/model caches, virtual environments, generated build outputs, and local IDE/tool metadata without excluding source packages whose architectural name is `build` (notably `corpus-builder/src/sibyl_corpus_builder/build/`). Normal concatenated LLM snapshots also exclude `docs/WORKLOG.md` and `docs/specs/archive/`, while retaining `docs/specs/active/`; full repository archives keep all of them.
