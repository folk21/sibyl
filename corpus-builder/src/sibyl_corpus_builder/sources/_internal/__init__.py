"""Private implementation layer for the source-ingestion feature.

Modules in this package implement the mechanics behind
:mod:`sibyl_corpus_builder.sources.api`: selection and registry persistence,
source-adapter dispatch, explicit network acquisition, artifact caching,
per-work failure isolation, preparation, registration, and deterministic
reports.

The package sits between the public ``sources`` facade and concrete source
adapters. Its contracts are intentionally feature-specific, so they should not
be promoted to ``corpus-core`` unless they remain meaningful without source
acquisition concepts.

Other features must not import this package directly. ``build`` and
``curation`` consume only the prepared canonical-source boundary published by
this feature and loaded through ``sibyl_corpus_core``.
"""
