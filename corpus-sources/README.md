# Sibyl corpus sources

`corpus-sources/` is the permanent source/provenance/rights registry. It contains metadata only: downloaded books, discovery selections, scans, machine translations, and production corpus artifacts remain outside Git.

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

## Adding many works from an author catalog

Do **not** create dozens of work records by hand first. For supported catalog sources, start in `corpus-builder/` with discovery:

```bash
sibyl-corpus discover \
  --url "http://az.lib.ru/d/dostoewskij_f_m" \
  --output data/work/dostoevsky-selection.toml
```

Review the generated selection, acquire only `include` entries, and optionally persist the concrete acquired versions later with `sibyl-corpus register`. Registration creates disabled candidate records with hashes and never approves/enables them.

See [`../docs/USAGE.md`](../docs/USAGE.md) and [`../docs/SOURCES.md`](../docs/SOURCES.md).

## Adding an individual work manually

1. Copy `works/_example.toml.example` to `works/<work-id>.toml` and fill in work identity, source URI, language/text role, provenance, and rights-review fields.
2. Add the work ID to at least one collection under `collections/`.
3. From the repository root, run `make validate-sources`.
4. Acquire/review the concrete artifact through `corpus-builder`, record its raw/canonical SHA-256 values, pin the edition/revision/artifact, and complete rights review.
5. Only then set the record to approved/enabled for publishable corpus builds.

A foreign original may declare `russian_display_policy = "build_time_machine_translation"`; any generated Russian text must later be stored as a separate, explicitly labelled machine-translation text version.

For local candidate preparation, existing registry sources support an explicit `--allow-unapproved` override; artifacts produced under that override are not publishable.

Detailed policy is in [`../docs/SOURCES.md`](../docs/SOURCES.md). See also [`AGENTS.md`](AGENTS.md).
