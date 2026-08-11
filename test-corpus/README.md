# Sibyl test corpus

This directory contains a tiny **synthetic** corpus for deterministic repository tests and smoke builds. It is not presented as classical literature.

Contents:

- `sources/manifest.json` — fixture source manifest;
- `sources/*.txt` — synthetic fixture texts.

Run the end-to-end fixture build from the repository root:

```bash
make smoke-corpus
```

Production literary corpora belong outside this directory and require explicit provenance/rights metadata in `corpus-sources/`.
