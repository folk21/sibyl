# Test corpus implementation

## Scope

`test-corpus/` provides the smallest deterministic source input that can exercise the corpus-builder without network access, copyrighted production text, or external models.

## Contents

`sources/manifest.json` describes synthetic source documents and `sources/*.txt` contains deliberately invented fixture text. The fixture uses the same preparation/build contracts as real input where practical, but does not attempt to model production corpus size or literary quality.

## Usage

From the repository root:

```bash
make smoke-corpus
```

The target builds into a temporary directory, validates the resulting `corpus.db`, and removes the temporary output. The fixture configuration uses deterministic hint/embedding providers, so default smoke tests require no network or model download.

## Boundary

Production books, scans, model files, indexes, private user questions, and real saved encounters must never be added here. Real source identity belongs in `corpus-sources/`; generated production artifacts remain outside Git.
