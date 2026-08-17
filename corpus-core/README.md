# Sibyl corpus core

`corpus-core/` is the feature-neutral Python foundation shared by Sibyl corpus tooling. It owns canonical-source contracts and small deterministic primitives that make sense independently of source acquisition, automatic embeddings, or large-LLM curation.

It is **not** a runtime corpus format package and does not replace `corpus-format/`.

## Scope

Current shared responsibilities:

- `SourceDocument` — canonical prepared-source handoff contract;
- exact SHA-256 helpers;
- canonical `chars:start:end` locators;
- newline/text primitives shared by multiple features;
- atomic directory publication;
- loading deterministic prepared canonical sources.

Source-specific adapters, selection/registry logic, embeddings, SQLite corpus writing, and LLM proposal formats do not belong here.

## Setup

From the repository root, install `corpus-core` together with the builder:

```bash
python -m pip install -e ./corpus-core -e './corpus-builder[dev]'
```

Run focused tests:

```bash
make test-corpus-core
```

See [`IMPLEMENTATION.md`](IMPLEMENTATION.md) for the module map and [`AGENTS.md`](AGENTS.md) for dependency rules.
