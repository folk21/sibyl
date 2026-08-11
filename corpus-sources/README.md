# Sibyl corpus sources

`corpus-sources/` is the source/provenance/rights registry. It contains metadata only: downloaded books, scans, machine translations, and production corpus artifacts remain outside Git.

## Seed set

The repository currently includes **40 disabled candidate records**:

- 24 Russian classics (`collections/russian-classics.toml`);
- 12 foreign classics from Project Gutenberg (`collections/foreign-classics-ru.toml`);
- 4 philosophy/sacred-text candidates (`collections/sacred-and-philosophy.toml`).

All seed records are intentionally `review_status = "candidate"`, `rights_status = "review_required"`, and `enabled = false`. They are a review queue, not production approval.

Validate directly from the corpus-sources directory:

```bash
cd /path/to/sibyl/corpus-sources
python tools/validate_registry.py
```

or from the repository root:

```bash
make validate-sources
```

## Adding a work

1. Copy `works/_example.toml.example` to `works/<work-id>.toml` and fill in work identity, source URI, language/text role, provenance, and rights-review fields.
2. Add the work ID to at least one collection under `collections/`.
3. From the repository root, run `make validate-sources`.
4. Before enabling it, pin a concrete edition/revision/artifact and complete rights review.

A foreign original may declare `russian_display_policy = "build_time_machine_translation"`; any generated Russian text must later be stored as a separate, explicitly labelled machine-translation text version.

Detailed policy is in [`../docs/SOURCES.md`](../docs/SOURCES.md). See also [`AGENTS.md`](AGENTS.md).
