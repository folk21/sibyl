# Sibyl corpus sources

`corpus-sources/` is the permanent source/provenance/rights registry. It contains metadata only: downloaded books, discovery selections, scans, machine translations, and production corpus artifacts remain outside Git.

Current registry records are review material unless their concrete text versions satisfy the enabled-source approval rules. Do not mirror derived record counts here; inspect the registry or validator output when an exact current count matters.

## Validate

From the repository root:

```bash
make validate-sources
```

## Add works from a supported author catalog

Do not create many work records manually before discovery. Use the catalog workflow in [`../docs/WORKFLOW.md`](../docs/WORKFLOW.md): discover a review selection, acquire only intentional `include` entries, then optionally register the concrete acquired versions.

Registration creates disabled candidate records with pinned artifact hashes. It never approves or enables them.

## Add an individual work manually

1. Copy `works/_example.toml.example` to `works/<work-id>.toml` and fill in work identity, source URI, language/text role, provenance, and rights-review fields.
2. Add the work ID to at least one collection under `collections/`.
3. Run `make validate-sources` from the repository root.
4. Acquire or import the concrete artifact through `corpus-builder`, pin raw/canonical SHA-256 values and the concrete edition/revision/artifact, then complete rights review.
5. Only then mark the record approved/enabled for publishable corpus builds.

A foreign original may declare `russian_display_policy = "build_time_machine_translation"`; generated Russian text must later be stored as a separate, explicitly labelled machine-translation text version.

For local candidate preparation, existing registry sources support an explicit `--allow-unapproved` override. Output produced under that override is not publishable.

Detailed source policy is in [`../docs/SOURCES.md`](../docs/SOURCES.md). Command syntax is in [`../docs/USAGE.md`](../docs/USAGE.md), and current registry implementation is described in [`IMPLEMENTATION.md`](IMPLEMENTATION.md).
