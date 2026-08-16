# Sibyl corpus builder

`corpus-builder/` is a local Python build-time application. It discovers/reviews source catalogs, acquires explicitly selected source artifacts, produces canonical text, extracts exact passage candidates, and builds versioned Sibyl corpus artifacts. It is never embedded in the mobile runtime.

## Pipeline

```mermaid
flowchart LR
    U[Author/catalog URL] --> D[Discover]
    D --> S[Editable selection.toml]
    S --> R[Developer review]
    R --> A[Acquire included works]
    A --> C[Raw artifact cache + SHA-256]
    C --> N[Canonical text normalization]
    N --> P[Exact natural-boundary passages]
    P --> H[Retrieval text / semantic hints]
    H --> E[Embeddings]
    E --> W[Corpus writer]
    W --> V[Validation]
```

Importing the package never downloads sources or models. Network/model work happens only through explicit CLI commands/providers.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Install the optional ML dependencies only when building semantic vectors. The current ML environment requires Python 3.11 or 3.12 and uses pinned versions for reproducibility, including Intel macOS compatibility:

```bash
python3.12 -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[ml]'
```

If `python3.12` is unavailable, Python 3.11 is also supported. Do not install the ML extra from Python 3.13+ with the current dependency set.

## Discover and review a Lib.ru author page

The first batch-discovery adapter supports Lib.ru/Классика author pages. Give it an author/catalog URL:

```bash
sibyl-corpus discover \
  --url "http://az.lib.ru/d/dostoewskij_f_m" \
  --output data/work/dostoevsky-selection.toml
```

`discover` only writes a review manifest. It does **not** download books or change `corpus-sources/`.

Each candidate has one decision:

- `include` — literary work that will be acquired;
- `exclude` — ignored by later batch commands;
- `review` — ambiguous/non-fictional/editorial item requiring a developer decision.

Lib.ru correspondence/epistolary entries are automatically `exclude`. Literary prose/poetry/drama are normally `include`; manuscripts, criticism, journalism, memoirs, translations, diaries, and uncertain categories default to `review`.

Edit the TOML file before continuing. You may change decisions, remove entries, and optionally set `registry_work_id` before permanent registration.

## Acquire and prepare the reviewed selection

Acquire only entries explicitly marked `include`:

```bash
sibyl-corpus acquire \
  --selection data/work/dostoevsky-selection.toml \
  --cache data/raw
```

For Lib.ru, acquisition uses a source fallback chain: TXT first, the work-page HTML second, and FB2 last. The first artifact that can be normalized safely is cached with raw/canonical SHA-256 hashes. Normalizers are versioned as `libru_txt_v1`, `libru_html_v1`, and `libru_fb2_v1`.

A failure in one included work does not discard successful acquisitions from the same batch. The command writes a report next to the selection by default, for example `data/work/dostoevsky-selection-acquire-report.toml`, and exits non-zero after processing the batch when failures remain. Use `--report <path>` to choose another report location.

Materialize all included books as deterministic builder input:

```bash
sibyl-corpus prepare-selection \
  --selection data/work/dostoevsky-selection.toml \
  --cache data/raw \
  --output data/work/dostoevsky
```

Review passage extraction before building vectors:

```bash
sibyl-corpus inspect-passages \
  --config config/real-text.toml \
  --source data/work/dostoevsky \
  --output data/work/dostoevsky-passages.jsonl
```

## Register the selected concrete versions

Registration is optional during early local experiments. After acquisition/review, persist the included works as disabled candidate records with pinned artifact hashes:

```bash
sibyl-corpus register \
  --selection data/work/dostoevsky-selection.toml \
  --cache data/raw \
  --registry ../corpus-sources \
  --collection dostoevsky-libru
```

Registration never enables or approves a source. It creates new work records and one collection and refuses to overwrite an existing work; merge an additional Lib.ru text version into an existing registry work manually when necessary.

## Existing single-source workflow

Project Gutenberg still has an automatic plain-text fetch adapter for already registered sources:

```bash
sibyl-corpus fetch \
  --registry ../corpus-sources \
  --work melville-moby-dick \
  --cache data/raw \
  --allow-unapproved
```

For source families without a safe automatic parser, import a manually reviewed UTF-8 text artifact:

```bash
sibyl-corpus import-file \
  --registry ../corpus-sources \
  --work chekhov-lady-with-the-dog \
  --file /path/to/reviewed-source.txt \
  --cache data/raw \
  --allow-unapproved
```

Then materialize deterministic builder input with `sibyl-corpus prepare`.

## Build a real development corpus

The first real-text configuration indexes exact passage text directly. This deliberately postpones LLM-generated semantic hints so retrieval quality can be measured in stages.

```bash
sibyl-corpus build \
  --config config/real-text.toml \
  --source data/work/dostoevsky \
  --output data/output/dostoevsky

sibyl-corpus validate --corpus data/output/dostoevsky/corpus.db
```

`config/real-text.toml` uses the opt-in `sentence_transformers` provider with `intfloat/multilingual-e5-small`. The first run may download model files through Sentence Transformers; default tests never use this provider.
The config also records the asymmetric E5 prefixes: `passage: ` for indexed passage text and `query: ` for runtime questions. Both are persisted so runtime compatibility can be checked explicitly.

Real-text builds show explicit stages and an embedding progress bar. Completed embedding batches are committed to `data/work/<prepared-source>/.embedding-cache/`. If a build is interrupted, rerunning the same command reuses completed vectors and computes only missing inputs. The cache key includes the embedding provider/model/dimensions/normalization/passage-prefix configuration plus the exact embedding input text hash, so incompatible settings do not silently reuse vectors. A fully cached rebuild does not load the embedding model.

### Download the Desktop runtime model bundle

The corpus build uses Python/Sentence Transformers, but Desktop inference uses local ONNX Runtime. Download the matching ignored development bundle once:

```bash
sibyl-corpus download-runtime-model \
  --config config/real-text.toml \
  --output data/runtime-models/multilingual-e5-small
```

The command downloads the official optimized ONNX model and `tokenizer.json`, records SHA-256 hashes and runtime assumptions in `model-manifest.json`, and publishes only after the bundle is complete. This is an explicit network command; imports/default tests never download runtime models.

## Development fixture

The deterministic fixture path remains model-free:

```bash
sibyl-corpus build \
  --config config/example.toml \
  --source ../test-corpus/sources \
  --output data/output/demo
```

From the repository root, `make smoke-corpus` runs the same idea in a temporary directory.

## Generated local data

`corpus-builder/data/` is entirely local/generated and ignored by Git; this includes raw downloads, prepared work, embedding caches, and published development outputs. Raw source artifacts, downloaded books, model files, and production corpus packages must not be committed or included in shareable repository archives.

## Detailed docs

- [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — current Python modules, pipeline orchestration, caching, and publication internals.
- [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- [`../docs/CONFIGURATION.md`](../docs/CONFIGURATION.md)
- [`../docs/SOURCES.md`](../docs/SOURCES.md)
- [`../docs/CORPUS_FORMAT.md`](../docs/CORPUS_FORMAT.md)
- [`../docs/TESTS.md`](../docs/TESTS.md)
- [`AGENTS.md`](AGENTS.md)
