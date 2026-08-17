# Usage

For the primary **where to start / what to run next** path, begin with [`WORKFLOW.md`](WORKFLOW.md). This document is the command-oriented reference for the individual operations used by that workflow.

## Interactive development

From the repository root:

```bash
make run-desktop
```

The Desktop harness uses the same shared Compose `SibylApp()` as Android. `make run-desktop` keeps the deterministic synthetic demo mode; `make run-desktop-real` loads a built local corpus and matching local ONNX model bundle.

## Command reference: prepare a real author catalog

Corpus preparation is intentionally separated from runtime development. For Russian classics, the first convenient batch workflow starts from a Lib.ru/Классика author page.

All commands below are run from `corpus-builder/`.

### 1. Discover works

```bash
sibyl-corpus discover \
  --url "http://az.lib.ru/d/dostoewskij_f_m" \
  --output data/work/dostoevsky-selection.toml
```

The command does not download books. It produces an editable selection manifest with `include`, `exclude`, and `review` decisions. Correspondence/epistolary entries are automatically excluded.

### 2. Review the generated selection

Open:

```text
data/work/dostoevsky-selection.toml
```

Change decisions or remove entries. Only `decision = "include"` is processed later. `review` is intentionally not treated as include.

Optionally fill `registry_work_id` for stable permanent IDs before registration.

### 3. Acquire the included works

```bash
sibyl-corpus acquire \
  --selection data/work/dostoevsky-selection.toml \
  --cache data/raw
```

For Lib.ru, the builder tries source artifacts in this order:

1. TXT exposed or derivable from the work page;
2. the work-page HTML, extracting only the literary body;
3. FB2/FB2 ZIP as a final fallback.

The first safely normalized artifact is cached with raw/canonical hashes. Acquisition is per-work: one malformed source does not discard successful books. By default the command writes `data/work/dostoevsky-selection-acquire-report.toml` with `acquired`, `failed`, and `skipped` items. If any included work fails, the command exits non-zero **after** processing the whole selection so the report can be reviewed and the command retried.

### 4. Materialize canonical builder input

```bash
sibyl-corpus prepare-selection \
  --selection data/work/dostoevsky-selection.toml \
  --cache data/raw \
  --output data/work/dostoevsky
```

### 5A. Optional large-LLM curation branch

Once `data/work/<author>/` exists, the LLM-curation path branches **before** automatic passage inspection. Export the canonical texts and stable guided questions without running the splitter:

```bash
sibyl-corpus export-curation-bundle \
  --source data/work/dostoevsky \
  --questions ../corpus-curation/questions.json \
  --output data/curation/dostoevsky-curation-bundle.zip
```

The exporter requires approved rights metadata by default. `--allow-unapproved` is available only as an explicit development override after separately confirming that the concrete text may be sent to the external model/service.

After an external large LLM returns a locator/hash proposal in `corpus-curation/proposals/`, validate and normalize it locally:

```bash
sibyl-corpus import-curation \
  --source data/work/dostoevsky \
  --questions ../corpus-curation/questions.json \
  --input ../corpus-curation/proposals/dostoevsky-v1.json \
  --output ../corpus-curation/curated/dostoevsky-v1.json

sibyl-corpus validate-curation \
  --source data/work/dostoevsky \
  --questions ../corpus-curation/questions.json \
  --curation ../corpus-curation/curated/dostoevsky-v1.json
```

The importer re-resolves the exact canonical character slice and verifies both canonical and selected-text SHA-256 values. The committed curation metadata contains no passage text. See [`WORKFLOW.md`](WORKFLOW.md) for the complete human/LLM/Python handoff and current runtime status.

### 5B. Review automatic passage candidates

```bash
sibyl-corpus inspect-passages \
  --config config/real-text.toml \
  --source data/work/dostoevsky \
  --output data/work/dostoevsky-passages.jsonl
```

Each passage has an exact canonical-text `chars:start:end` locator and a hard `max_words` limit. Long paragraphs are split at sentence boundaries when possible, with a word-boundary fallback rather than mid-character truncation.

### 6. Optionally register the concrete source versions

Once the selection/artifacts are worth keeping in the project registry:

```bash
sibyl-corpus register \
  --selection data/work/dostoevsky-selection.toml \
  --cache data/raw \
  --registry ../corpus-sources \
  --collection dostoevsky-libru
```

This creates disabled candidate records with hashes; it does not approve or enable them. Existing registry works are never overwritten.

### 7. Build semantic vectors and corpus artifacts

Install the opt-in ML dependencies once in a Python 3.11/3.12 environment. On machines whose default Python is newer, use a separate ML virtual environment:

```bash
python3.12 -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ../corpus-core -e '.[ml]'
```

Python 3.11 is also supported for this environment. The current ML extra is pinned so corpus embeddings are built with a reproducible dependency stack.

Then:

```bash
sibyl-corpus build \
  --config config/real-text.toml \
  --source data/work/dostoevsky \
  --output data/output/dostoevsky

sibyl-corpus validate --corpus data/output/dostoevsky/corpus.db
```

The initial real-text configuration uses `multilingual-e5-small` via Sentence Transformers and indexes exact passage text itself. LLM-generated semantic hints are intentionally deferred so their value can be evaluated separately.

During the embedding stage the builder prints cache statistics and a progress bar. Completed batches are stored under `data/work/<prepared-source>/.embedding-cache/`, outside published corpus output. `Ctrl+C` may discard the currently running batch, but previously completed batches remain reusable. Rerun the same `build` command to resume; a fully cached build skips loading the ML model. Changing model/provider/dimensions/normalization/passage prefix selects a different cache namespace, while changing passage text naturally produces a new text hash.

### Run the built corpus in Desktop

`multilingual-e5-small` uses asymmetric E5 prefixes: corpus passages are embedded with `passage: ` and runtime questions with `query: `. The current real-text config persists both assumptions in `manifest.json`. If your corpus was built before `query_prefix` was added, rerun the same `build` command; completed passage embeddings are reused from the embedding cache.

Download the runtime-only ONNX/tokenizer bundle once:

```bash
sibyl-corpus download-runtime-model \
  --config config/real-text.toml \
  --output data/runtime-models/multilingual-e5-small
```

Then, from the repository root:

```bash
make run-desktop-real
```

The default paths are:

```text
corpus-builder/data/output/dostoevsky
corpus-builder/data/runtime-models/multilingual-e5-small
```

Override them when needed:

```bash
make run-desktop-real \
  CORPUS_DIR=corpus-builder/data/output/other-corpus \
  MODEL_DIR=corpus-builder/data/runtime-models/multilingual-e5-small
```

Desktop validates corpus format/model/dimensions/query-prefix compatibility before opening the real retrieval flow. It then uses local ONNX query embedding, brute-force cosine search over `vectors.json`, SQLite passage lookup from `corpus.db`, and the shared controlled-random `SelectionEngine`. No question or passage is sent to a backend.

On Intel macOS, export the locally built DJL tokenizer native described in [`INSTALLATION.md`](INSTALLATION.md) before running real mode. Concrete Desktop classes and library responsibilities are mapped in [`../mobile/IMPLEMENTATION.md`](../mobile/IMPLEMENTATION.md).

## Existing single-source workflow

For a registered Project Gutenberg work:

```bash
sibyl-corpus fetch \
  --registry ../corpus-sources \
  --work melville-moby-dick \
  --cache data/raw \
  --allow-unapproved
```

For a reviewed local UTF-8 artifact:

```bash
sibyl-corpus import-file \
  --registry ../corpus-sources \
  --work chekhov-lady-with-the-dog \
  --file /path/to/reviewed-source.txt \
  --cache data/raw \
  --allow-unapproved
```

Then use `sibyl-corpus prepare` with one or more `--work` arguments.

## Synthetic smoke build

From the repository root:

```bash
make smoke-corpus
```

This path remains deterministic and does not download texts or models.

## Source approval

Discovery/acquisition is not approval. Before any corpus is distributed, pin the concrete artifact/edition, record raw/canonical hashes, complete rights review, and enable only approved source versions. See [`SOURCES.md`](SOURCES.md).
