# Development

## Repository workflow

Before changing code:

1. read root `AGENTS.md`;
2. read the nearest subproject `AGENTS.md`;
3. inspect the current README/code/tests for that scope;
4. identify the owning document under root `docs/`;
5. make the smallest coherent change;
6. run focused validation, then broader checks.

## Documentation ownership

Detailed documentation lives only in root `docs/`. Subprojects keep:

- `README.md` — local purpose, quick start, module/file map, links to owning root docs;
- `AGENTS.md` — local invariants and validation rules.

Do not recreate `mobile/docs/`, `corpus-builder/docs/`, `corpus-format/docs/`, or `corpus-sources/docs/` unless the documentation strategy is intentionally reconsidered.

## Format changes

A persisted contract change should normally update together:

- `corpus-format/` schema/manifest/version;
- `corpus-builder/` writer/validation;
- `mobile/` domain/reader assumptions when applicable;
- compatibility/focused tests;
- [`CORPUS_FORMAT.md`](CORPUS_FORMAT.md) and roadmap/changelog as needed.

## Source changes

For catalog-scale additions, prefer `sibyl-corpus discover` → developer review → resilient `acquire` (review its per-work report) before creating permanent registry records. `register` may then create disabled candidate records with pinned hashes. For individual additions, a work record + collection membership remains valid.

Enabling any source requires pinned provenance and approved rights metadata. Run `make validate-sources` after permanent registry changes.

See [`SOURCES.md`](SOURCES.md).

## Development loop

For interactive work on shared behavior/UI, prefer the Desktop harness:

```bash
make run-desktop
```

Use Android when validating Android-specific integration rather than for every UI/domain iteration.

## Tests

Use [`TESTS.md`](TESTS.md) as the test command matrix. The standard pre-merge order, run from the repository root, is:

```bash
make check
make test-desktop  # when shared behavior/UI is affected
make test-mobile   # when shared or Android behavior/contracts are affected
```

Production model downloads, large real corpora, external APIs, and GPU jobs are excluded from default tests.

## Generated artifacts

Never commit production `corpus.db`, ANN indexes, ONNX models, downloaded books/scans, generated translations, embedding caches, or transient builder outputs unless a deliberate tiny fixture is documented and reviewed. `corpus-builder/data/` is reserved for local/generated data; committed tiny fixtures belong under `test-corpus/`.

## Repository snapshots

Use `archive.sh` for shareable full ZIP archives and `concat_sibyl.sh` for source-only concatenated text snapshots. Both helper paths exclude `corpus-builder/data/`, local virtual environments, model/download caches, Gradle/Kotlin caches, IDE metadata, and generated build outputs. Keep generated snapshot files outside the repository when practical.

## Archive handoff

- Complete repository archives use `sibyl/` as the top-level directory and include `FULL` in the filename.
- Patch archives use `sibyl/` as the top-level directory, include `PATCH` in the filename, and contain only added/modified files.
- ZIP extraction cannot represent deletion semantics; every handoff must explicitly list deleted paths, or state `none`.
