# Corpus core development rules

Root `AGENTS.md` also applies.

## Purpose

`corpus-core/` contains only feature-neutral Python contracts and deterministic primitives shared by more than one corpus feature.

Use this test before moving code here:

> Would this API still make sense if source acquisition, automatic embeddings, and LLM curation were replaced by different implementations?

If not, keep the code in the owning `corpus-builder` feature, usually under that feature's `_internal` package.

## Dependency boundary

- `sibyl_corpus_core` must never import `sibyl_corpus_builder`.
- Core must not know about Lib.ru, Project Gutenberg, selection manifests, source registry records, embedding providers, LLM proposal schemas, or runtime SQLite schema details.
- `corpus-format/` remains the owner of persisted runtime corpus semantics; do not move SQL/manifest format ownership into core.
- Keep imports side-effect free: no network, model loading, or generated-data writes on import.

## Exact text

- `SourceDocument.text` is canonical source text.
- Locator helpers use half-open exact character ranges.
- Hash helpers operate on exact bytes/UTF-8 text and must not normalize content implicitly.
- Shared text helpers may perform only explicitly named mechanical operations such as newline normalization.

## Documentation and tests

Every Python package must have a meaningful `__init__.py` package docstring that explains its architectural role and dependency boundary. Keep it to one or two short paragraphs when possible; detailed pipeline/module descriptions belong in `IMPLEMENTATION.md`.

Every non-obvious module should explain where it sits in the corpus pipeline and what it intentionally does not own. Add deterministic tests for shared contracts and update [`IMPLEMENTATION.md`](IMPLEMENTATION.md) when modules move or responsibilities change.

```bash
make test-corpus-core
```
