"""Private mechanics for the automatic corpus-build feature.

This package implements the stages orchestrated by
:mod:`sibyl_corpus_builder.build.api`: natural-boundary automatic splitting,
semantic hint construction, embedding providers and resumable caching,
runtime SQLite/manifest writing, validation, and Desktop runtime-model bundle
support.

The code here assumes build-specific concepts and is therefore intentionally
not part of ``corpus-core``. Callers outside the ``build`` feature should use
the public API rather than importing these modules directly, and other builder
features must not depend on this private package.

The automatic splitter is a deterministic retrieval fallback, not a literary
curator. Exact stored text, compatibility checks, reproducible IDs, and atomic
publication remain invariants even though the selection of automatic passage
boundaries is mechanical.
"""
