# Usage

[`WORKFLOW.md`](WORKFLOW.md) owns the end-to-end **what do I run next?** sequence. This document is the command/option reference: use it when you already know which stage you are operating or need an alternate input/flag.

Unless noted otherwise, `sibyl-corpus` commands run from `corpus-builder/`.

## Runtime development

From the repository root:

| Command | Purpose |
|---|---|
| `make build-runtime-corpus` | Rebuild the single runtime corpus from all locally prepared source sets and compatible curated metadata/validated machine translations. |
| `make run-desktop` | Run the deterministic synthetic Compose Desktop demo. |
| `make run-desktop-real` | Run Desktop with the default generated corpus/model paths. |
| `make run-desktop-real CORPUS_DIR=<dir> MODEL_DIR=<dir>` | Run Desktop with explicit generated corpus/model directories. |
| `make download-runtime-model` | Download the default local ONNX/tokenizer bundle. |

Real Desktop mode validates corpus/model compatibility before retrieval. Intel macOS native-tokenizer setup is documented only in [`INSTALLATION.md`](INSTALLATION.md).

## Source-ingestion commands

### `discover`

Creates an editable developer-review selection from a supported author/catalog URL.

```text
sibyl-corpus discover \
  --url <catalog-url> \
  [--language <language>] \
  [--original-language <language>] \
  --output <selection.toml>
```

Discovery performs no acquisition and grants no approval. Lib.ru discovery supports both traditional `text_*.shtml` work pages and direct `.txt` catalog entries. Existing Russian catalogs default to `ru`; use `--language en` (or another explicit language) for foreign originals. When `--original-language` is omitted after a language override, it defaults to the discovered text language. Use a different original language only when the selected text itself is a translation.

Shakespeare example:

```bash
sibyl-corpus discover \
  --url "https://lib.ru/SHAKESPEARE/ENGL/" \
  --language en \
  --output data/work/shakespeare-selection.toml
```

The generated selection is a review artifact. Before `acquire`, edit wanted entries to `decision = "include"`; entries left as `review` are not acquired. For classification and provenance behavior, see [`SOURCES.md`](SOURCES.md).

### `acquire`

Processes only `decision = "include"` entries in a reviewed selection and caches the first safely normalized source artifact for each work.

```text
sibyl-corpus acquire --selection <selection.toml> --cache <cache-dir> [--report <report.toml>]
```

Precondition: the selection must contain at least one `decision = "include"` entry. If every entry is still `review`/`exclude`, acquisition stops and asks for explicit review rather than implicitly approving anything.

Shakespeare example:

```bash
sibyl-corpus acquire \
  --selection data/work/shakespeare-selection.toml \
  --cache data/raw
```

Batch failures are isolated per work. Successful artifacts remain cached even when other included works fail, and a later `acquire` run reuses valid cached artifacts instead of downloading them again. Lib.ru direct-TXT requests are paced and retried when a response cannot be normalized as literary content, because `.txt` URLs may be rendered as HTML and may occasionally return transient service pages during bursty access. The command finishes the selection, writes a report, then exits non-zero if included works still failed after their candidate attempts. Re-running the same command reuses already successful cached artifacts during the later preparation stage.

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

## Build-time machine-translation commands

These commands translate only already validated curated passages. Generated target text stays under ignored local `corpus-builder/data/`.

### `export-translation-bundle`

```text
sibyl-corpus export-translation-bundle \
  --source <prepared-dir> \
  --questions <questions.json> \
  --curation <curated.json> \
  --target-language <lang> \
  --output <bundle.zip> [--allow-unapproved]
```

The bundle contains exact curated source text and deterministic source hashes. Export requires approved source rights metadata by default; `--allow-unapproved` is an explicit local-review override after separately confirming external-service upload rights. Passages already in the target language are omitted; export fails if nothing requires translation.

### `import-translation`

```text
sibyl-corpus import-translation \
  --source <prepared-dir> \
  --questions <questions.json> \
  --curation <curated.json> \
  --target-language <lang> \
  --input <translation-proposal.json> \
  --output <validated-translation.json>
```

The proposal must be complete for the exported bundle and identify `translation_provider`, `translation_model`, `prompt_version`, and `translation_method = "large_llm"`. Import pins every generated text to an exact curated `passage_id`/source hash and derives target-text SHA-256 without rewriting the generated literary wording.

### `validate-translation`

```text
sibyl-corpus validate-translation \
  --source <prepared-dir> \
  --questions <questions.json> \
  --curation <curated.json> \
  --translation <validated-translation.json>
```

Revalidates generated text against the current canonical source and curated passage identities.

## Automatic-build commands

### `inspect-passages`

Writes the deterministic automatic splitter output as JSON Lines for review.

```text
sibyl-corpus inspect-passages --config <config.toml> --source <prepared-dir> --output <passages.jsonl>
```

The splitter preserves exact canonical `chars:start:end` locators and natural boundaries where possible. It is a mechanical generic-retrieval path, not literary curation.

### `build-available`

Builds the normal local runtime corpus from every prepared source set currently available beneath one work root. This is the preferred command when authors are prepared incrementally.

```text
sibyl-corpus build-available \
  --config <config.toml> \
  --source-root <prepared-root> \
  --questions <questions.json> \
  --curation-root <curated-dir> \
  [--translation-root <validated-translations-dir>] \
  --output <corpus-dir>
```

`--source-root` considers only immediate child directories containing a prepared `manifest.json`; raw/acquired directories that have not reached preparation are ignored. Curated `*.json` files are selected when all of their referenced `(work_id, text_version_id)` values are present in the discovered prepared source sets. Validated translation `*.json` files are selected when every curated `passage_id` they require is present; entirely unavailable translations are skipped and partially available ones are rejected. Curations for entirely unavailable authors are skipped; a partially available curation is rejected instead of being silently truncated. All selected curation is then revalidated against exact canonical text before publication.

The repository convenience target uses this command with the standard local paths and publishes one current runtime corpus directly at `corpus-builder/data/output`:

```bash
make build-runtime-corpus
```

Re-running the command after preparing a new author rebuilds only the final immutable runtime artifact. Compatible embedding caches from all discovered source sets are reused, so existing authors do not need to be re-embedded.

### `build`

Builds a format-v4 runtime corpus from explicitly selected prepared source directories. Keep this command for focused/debug builds and future filtered assembly; the normal all-available workflow uses `build-available`.

```text
sibyl-corpus build --config <config.toml> \
  --source <prepared-dir> [--source <prepared-dir-2> ...] \
  [--questions <questions.json>] \
  [--curation <curated.json> ...] \
  [--translation <validated-translation.json> ...] \
  --output <corpus-dir>
```

`--source`, `--curation`, and `--translation` are repeatable. Prepared source sets are composed in memory; duplicate text-version identities and conflicting metadata for the same `work_id` are rejected instead of being silently merged. Supplying any `--curation` requires `--questions`. Curation inputs are revalidated against the combined prepared canonical sources during assembly.

With `config/real-text.toml`, both build modes use the optional Sentence Transformers provider and `intfloat/multilingual-e5-small` for free-form retrieval. Compatible embedding caches are read from every prepared source directory; curated passages do not receive query embeddings merely to support guided lookup.

### `validate`

```text
sibyl-corpus validate --corpus <corpus.db>
```

Validates required format-v4 runtime metadata, foreign keys, guided schema integrity, and non-empty free-form passage/hint content.

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
