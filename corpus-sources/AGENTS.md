# Corpus sources development rules

Root `AGENTS.md` also applies.

## Purpose

`corpus-sources/` owns candidate/approved source declarations and rights/provenance records. It does not own passage extraction, embeddings, ranking, or mobile behavior.

## Source invariants

- Production-enabled records register a concrete text version, not merely a title.
- Disabled `candidate` records may point to a discovery/landing page while edition/revision review is pending.
- Record language, text role, source identity, provenance, rights review, and category.
- Treat original, human translation, and machine translation as separate text versions.
- Never infer translation rights from the age of the original.
- For sacred texts, distinguish textual/translation tradition when relevant.
- Do not commit downloaded books/scans/generated translations/production corpora.
- Do not set `enabled = true` until review status and all enabled text-version rights are approved and the source locator is pinned.

## Networking

Future downloaders must be explicit CLI operations. Reading/validating the registry must never trigger network access.

## Validation

```bash
python tools/validate_registry.py
```

See root `docs/SOURCES.md` and `docs/TESTS.md`.
