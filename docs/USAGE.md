# Usage

[`WORKFLOW.md`](WORKFLOW.md) owns the end-to-end **what do I run next?** sequence. This document is the command/option reference: use it when you already know which stage you are operating or need an alternate input/flag.

Unless noted otherwise, `sibyl-corpus` commands run from `corpus-builder/`.

## Runtime development

From the repository root:

| Command | Purpose |
|---|---|
| `make run-desktop` | Run the deterministic synthetic Compose Desktop demo. |
| `make run-desktop-real` | Run Desktop with the default generated corpus/model paths. |
| `make run-desktop-real CORPUS_DIR=<dir> MODEL_DIR=<dir>` | Run Desktop with explicit generated corpus/model directories. |
| `make download-runtime-model` | Download the default local ONNX/tokenizer bundle. |

Real Desktop mode validates corpus/model compatibility before retrieval. Intel macOS native-tokenizer setup is documented only in [`INSTALLATION.md`](INSTALLATION.md).

## Source-ingestion commands

### `discover`

Creates an editable developer-review selection from a supported author/catalog URL.

```text
sibyl-corpus discover --url <catalog-url> --output <selection.toml>
```

Discovery performs no acquisition and grants no approval. For Lib.ru classification behavior, see [`SOURCES.md`](SOURCES.md).

### `acquire`

Processes only `decision = "include"` entries in a reviewed selection and caches the first safely normalized source artifact for each work.

```text
sibyl-corpus acquire --selection <selection.toml> --cache <cache-dir> [--report <report.toml>]
```

Batch failures are isolated per work. The command finishes the selection, writes a report, then exits non-zero if included works failed.

### `prepare-selection`

Materializes deterministic canonical input for all included works in a reviewed selection.

```text
sibyl-corpus prepare-selection --selection <selection.toml> --cache <cache-dir> --output <prepared-dir>
```

The resulting prepared directory is the shared handoff to both automatic build and LLM curation.

### `register`

Persists acquired selection items as disabled candidate source records and a collection.

```text
sibyl-corpus register --selection <selection.toml> --cache <cache-dir> --registry <registry-dir> [--collection <id>]
```

Registration never approves/enables records and never overwrites an existing work.

### `fetch`

Acquires one existing registry text version through its source adapter.

```text
sibyl-corpus fetch --registry <registry-dir> --work <work-id> [--version <version-id>] --cache <cache-dir> [--allow-unapproved]
```

`--allow-unapproved` is a local-review override only; artifacts produced from unapproved sources are not publishable.

### `import-file`

Imports a manually reviewed local artifact into the same source cache.

```text
sibyl-corpus import-file --registry <registry-dir> --work <work-id> [--version <version-id>] --file <path> --cache <cache-dir> [--allow-unapproved]
```

The current import path expects an explicitly reviewed UTF-8 artifact.

### `prepare`

Materializes prepared canonical input from cached registry sources. Repeat `--work` to include several works.

```text
sibyl-corpus prepare --registry <registry-dir> --work <work-id> [--work <work-id> ...] --cache <cache-dir> --output <prepared-dir> [--allow-unapproved]
```

## LLM-curation commands

Curation starts from prepared canonical input; it does **not** depend on automatic passage splitting.

### `export-curation-bundle`

```text
sibyl-corpus export-curation-bundle --source <prepared-dir> --questions <questions.json> --output <bundle.zip> [--work <work-id> ...] [--approved-only | --allow-unapproved]
```

- repeat `--work` to export only selected prepared work IDs;
- export requires approved rights metadata by default and fails if any selected source version is unapproved;
- `--approved-only` skips unapproved source versions and fails if none remain;
- `--allow-unapproved` includes unapproved versions only after separately confirming that the concrete text may be sent to the external model/service;
- `--approved-only` and `--allow-unapproved` are mutually exclusive.

The ZIP contains canonical literary texts and therefore belongs under ignored local `corpus-builder/data/` paths, never Git.

### `import-curation`

```text
sibyl-corpus import-curation --source <prepared-dir> --questions <questions.json> --input <proposal.json> --output <curated.json>
```

The importer treats the LLM output as untrusted metadata. It resolves every locator against local canonical text and verifies canonical/text SHA-256 values before writing normalized Git-safe metadata.

### `validate-curation`

```text
sibyl-corpus validate-curation --source <prepared-dir> --questions <questions.json> --curation <curated.json>
```

Use after canonical-source or curated-metadata changes. Stale hashes/locators fail validation rather than being retargeted silently.

## Automatic-build commands

### `inspect-passages`

Writes the deterministic automatic splitter output as JSON Lines for review.

```text
sibyl-corpus inspect-passages --config <config.toml> --source <prepared-dir> --output <passages.jsonl>
```

The splitter preserves exact canonical `chars:start:end` locators and natural boundaries where possible. It is a mechanical generic-retrieval path, not literary curation.

### `build`

Builds the current runtime corpus from prepared canonical sources.

```text
sibyl-corpus build --config <config.toml> --source <prepared-dir> --output <corpus-dir>
```

With `config/real-text.toml`, the build uses the optional Sentence Transformers provider and `intfloat/multilingual-e5-small`. Completed embedding inputs are cached under the prepared source directory and are reused when their exact text/configuration identity still matches.

### `validate`

```text
sibyl-corpus validate --corpus <corpus.db>
```

Validates required runtime database metadata, foreign keys, and non-empty passage/hint content.

### `download-runtime-model`

```text
sibyl-corpus download-runtime-model --config <config.toml> --output <model-dir>
```

This is an explicit network command that downloads the supported Desktop ONNX/tokenizer bundle and writes `model-manifest.json`. It never runs during imports/default tests.

## Synthetic smoke build

From the repository root:

```bash
make smoke-corpus
```

This uses synthetic fixtures, a deterministic embedding provider, a temporary output directory, and no network/model downloads.

## Source approval

Discovery, acquisition, or successful local build is not publication approval. Before distributing a corpus, pin the concrete source artifact/version, record required hashes/provenance, and complete rights review. [`SOURCES.md`](SOURCES.md) owns those rules.
