# AGENTS.md

This file contains repository-wide development rules for Sibyl. Read the nearest local `AGENTS.md` before changing `mobile/`, `corpus-builder/`, `corpus-format/`, `corpus-sources/`, or `test-corpus/`.

## Project summary

Sibyl is an offline-first literary discovery application. A user question is embedded locally, matched against semantic metadata for literary passages, and answered with an exact stored passage selected from a semantically plausible candidate pool using controlled randomness.

Primary scopes:

- `mobile/` — Kotlin Multiplatform runtime/UI with Android product and JVM Desktop development entry points;
- `corpus-builder/` — Python build-time preprocessing;
- `corpus-format/` — versioned persisted contract;
- `corpus-sources/` — source/provenance/rights registry;
- `test-corpus/` — synthetic fixtures.

There is no required backend in the core architecture.

## Language and documentation

- Write software code, comments, KDoc/docstrings, tests, config comments, examples, README/AGENTS files, and software documentation in English.
- Literary source text keeps its source language and exact approved wording.
- Avoid comments that restate code. Document useful contracts/invariants instead.
- Detailed documentation lives only under root `docs/`.
- Subprojects keep only `README.md` for local quick start and `AGENTS.md` for local change rules.
- Architecture/workflow diagrams should use Mermaid instead of ASCII/pseudo-text diagrams when a diagram is useful.

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
- `corpus-builder/` may depend on format/source declarations but must not execute mobile code.
- `corpus-format/` owns persisted semantics and must not depend on builder/mobile internals.
- `corpus-sources/` owns source/version declarations and review state, not passage extraction or ranking.
- Source discovery manifests are developer review artifacts: discovery may classify candidates but must never approve or publish them automatically.
- Platform-specific ONNX/index APIs stay behind small interfaces such as `EmbeddingEngine` and `VectorIndex`.
- The JVM Desktop app is a development harness: reuse shared UI/runtime code and do not introduce a REST/backend boundary just to run it locally.
- UI must not implement ranking, vector-search internals, or corpus parsing.

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
- `docs/ARCHITECTURE.md` — system boundaries and data flow;
- `docs/INSTALLATION.md` — toolchains/setup;
- `docs/TESTS.md` — test matrix;
- `docs/USAGE.md` — runtime/build workflows;
- `docs/CONFIGURATION.md` — configuration ownership;
- `docs/SOURCES.md` — source/provenance/rights/normalization policy;
- `docs/CORPUS_FORMAT.md` — persisted format semantics/versioning/validation;
- `docs/DEVELOPMENT.md` — contribution workflow;
- `docs/SECURITY_AND_PRIVACY.md` — privacy/content-integrity rules;
- `docs/ROADMAP.md` — prioritized work with explicit status;
- `docs/CHANGELOG.md` — completed repository changes;
- subproject `README.md` — local overview/commands/file map;
- local `AGENTS.md` — protected rules close to code.

## Repository archive checklist

1. Include no private user questions, real saved encounters, restricted texts, secrets, downloaded corpora, model files, generated production artifacts, caches, `.gradle`, `__pycache__`, or `.pytest_cache`.
2. Keep documented commands aligned with real targets/scripts.
3. Confirm corpus-format version metadata matches builder/mobile assumptions.
4. From the repository root, run `make check` and focused mobile tests where relevant.
5. Validate Markdown links and source-registry references.
6. Full generated archives must use `sibyl/` as the top-level directory.
7. Name complete repository archives with `FULL` and patch archives with `PATCH`. A patch archive contains only added/modified files under `sibyl/`; deleted paths must be reported explicitly because extracting a ZIP cannot delete them.
8. When handing off either a full archive or a patch, explicitly report the list of deleted files; write `none` when there are no deletions.
9. `archive.sh` and `concat_sibyl.sh` must exclude downloaded/generated corpus data, embedding/model caches, virtual environments, build outputs, and local IDE/tool metadata.
