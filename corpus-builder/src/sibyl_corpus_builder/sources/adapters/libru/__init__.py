"""Lib.ru discovery, resilient acquisition, and canonicalization adapter.

This package keeps all Lib.ru-specific behavior close together. ``discovery``
parses author catalog pages and creates conservative review decisions;
``fetch`` discovers candidate work artifacts and preserves the preferred
``TXT -> HTML -> FB2`` fallback order; ``normalize`` decodes Lib.ru text and
HTML representations, identifies the literary body, and removes recognized
site chrome without rewriting literary wording.

Pipeline position::

    Lib.ru author/work page
        -> discovery and developer review
        -> ordered artifact candidates
        -> source-specific normalization
        -> generic source artifact cache
        -> prepared canonical source

Canonicalization is versioned because hashes and exact character locators
ultimately depend on its output. A malformed candidate should fail locally and
allow acquisition to try the next candidate where the workflow permits it.
This package does not own selection persistence, registry approval, embeddings,
or LLM curation.
"""
