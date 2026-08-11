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

- `format_version` — target corpus-format version;
- `language` — primary target/display language.

### `[passages]`

- `min_words` — hard lower bound for development candidates;
- `preferred_words` — target size while combining natural paragraphs;
- `max_words` — hard upper bound;
- `overlap_paragraphs` — paragraph overlap between adjacent candidates.

Production preparation will generate explicit short/standard/extended variants instead of truncating runtime text.

### `[hints]`

- `hints_per_passage` — number of internal retrieval descriptions.

### `[embeddings]`

- `provider` — embedding adapter ID (`hash` is development-only);
- `dimensions`;
- `normalize`.

The published manifest must preserve model/provider identity and vector assumptions so mobile can reject incompatible packages.

## Source registry

Source records live in `corpus-sources/works/*.toml`; collections live in `corpus-sources/collections/*.toml`. Candidate records are disabled until source/version and rights review are complete.

See [`SOURCES.md`](SOURCES.md).

## Secrets

The default repository path requires no secrets. Future LLM/translation adapters may read environment variables during corpus builds. Never commit credentials, and never require a network secret for the core mobile question-to-passage flow.
