# Corpus sources implementation

## Scope

`corpus-sources/` is the permanent Git-tracked registry of source identity, provenance, rights review, and collection membership. It stores metadata, not downloaded books or generated corpus artifacts.

Policy is owned by [`../docs/SOURCES.md`](../docs/SOURCES.md); this document describes the current files and code that implement that policy.

## Layout

```text
corpus-sources/
├── works/         one TOML record per registered work
├── collections/   named lists of work IDs
└── tools/
    └── validate_registry.py
```

A work record contains work identity plus one or more concrete `text_versions`. Text-version records carry language/role, source family/URI/locator, rights state, provenance, optional translator or translation-provider metadata, and raw/canonical hashes when known.

## Candidate lifecycle

The registry intentionally permits disabled candidate records:

```mermaid
flowchart LR
    D[Discovered/acquired] --> C[candidate + review_required + disabled]
    C --> R[human provenance/rights review]
    R --> A[approved]
    A --> E[enabled for publishable builds]
```

`sibyl-corpus register` in the builder writes reviewed acquired selections as **disabled candidate records**. It does not approve rights, enable publication, or overwrite an existing work.

## Validation

`tools/validate_registry.py` loads every `works/*.toml` and verifies:

- schema version and controlled enums;
- unique work/text-version IDs;
- source URIs and optional hashes;
- collection references;
- stricter provenance/hash/rights requirements for `enabled = true` records.

Every work must be referenced by at least one collection.

## Relation to generated data

The registry is intentionally committed to Git because it is reproducible project metadata. The corresponding downloaded TXT/HTML/FB2, canonical text, prepared passages, embeddings, runtime models, and corpus packages live under `corpus-builder/data/` and are ignored.
