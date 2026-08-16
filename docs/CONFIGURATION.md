# Configuration

Configuration is split by responsibility. Do not create one global configuration object spanning runtime, corpus generation, and source review.

## Shared runtime

`SelectionPolicy` currently owns:

- `minSemanticScore` — minimum relevance gate;
- `semanticExponent` — strength of semantic similarity in sampling weight;
- `preferredLength` — preferred prepared passage variant.

Planned runtime policy fields include:

- ANN candidate-pool size;
- repeat/recency weighting;
- same-author/work penalties;
- semantic-cluster diversity;
- close/lateral/strange sampling proportions;
- installed corpus/category filters;
- display-language/translation preference.

User-facing response length should be semantic (`Short`, `Standard`, `Extended`), not a raw character/token slider. Hard min/max passage bounds belong to build-time configuration.

## Corpus builder

Builder configuration is TOML. See [`../corpus-builder/config/example.toml`](../corpus-builder/config/example.toml).

Current concepts:

### `[corpus]`

- `format_version` — target corpus-format version (currently `3`);
- `language` — primary target/display language.

### `[passages]`

- `min_words` — hard lower bound for development candidates;
- `preferred_words` — target size while combining natural paragraphs;
- `max_words` — hard upper bound;
- `overlap_paragraphs` — paragraph overlap between adjacent candidates.

Production preparation will generate explicit short/standard/extended variants instead of truncating runtime text.

### `[hints]`

- `provider` — `deterministic` for tests or `passage_text` for the first real-text retrieval baseline;
- `hints_per_passage` — number of internal retrieval descriptions. `passage_text` requires `1`.

### `[embeddings]`

- `provider` — embedding adapter ID (`hash` is deterministic development-only; `sentence_transformers` is opt-in build-time ML);
- `model_id` — required for Sentence Transformers;
- `dimensions`;
- `normalize`;
- `passage_prefix` — model-specific build-time prefix such as `passage: ` for E5 passage embeddings;
- `query_prefix` — matching runtime query prefix such as `query: `; it is persisted in the corpus manifest and validated by Desktop before local retrieval;
- `batch_size` — number of missing embedding inputs computed before each durable cache checkpoint;
- `cache` — enable the local resumable embedding cache. The real-text profile enables it; deterministic fixture builds disable it.

The published manifest must preserve model/provider identity and vector assumptions so mobile can reject incompatible packages.

## Guided questions and LLM curation

The stable guided-question product catalog is not builder TOML configuration. It lives in `corpus-curation/questions.json` and has its own `catalog_id`; curation mappings reference stable question IDs. A semantic catalog rewrite requires a new catalog ID rather than silently reinterpreting existing mappings.

LLM curation proposals and normalized mappings live under `corpus-curation/`. Full canonical text exported for the external model belongs only to ignored local `corpus-builder/data/curation/`. See [`WORKFLOW.md`](WORKFLOW.md).

## Source discovery and registry

Editable discovery manifests live under local `corpus-builder/data/work/` and are not committed. The selection schema uses `include` / `exclude` / `review`; batch acquisition processes only explicit `include`. `registry_work_id` is optional until permanent registration.

Permanent source records live in `corpus-sources/works/*.toml`; collections live in `corpus-sources/collections/*.toml`. Candidate records are disabled until source/version and rights review are complete.

See [`SOURCES.md`](SOURCES.md).

## Secrets

The default repository path requires no secrets. Future LLM/translation adapters may read environment variables during corpus builds. Never commit credentials, and never require a network secret for the core mobile question-to-passage flow.


`corpus-builder/config/real-text.toml` is the first real-corpus evaluation profile. It is intentionally separate from the deterministic default config so `make check` never downloads a model.
