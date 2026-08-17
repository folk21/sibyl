"""Feature-neutral canonical-source contracts and deterministic corpus primitives.

``sibyl_corpus_core`` is the shared Python boundary used by independent corpus
features after source text has been normalized. It owns the immutable
``SourceDocument`` contract plus small deterministic primitives for prepared
source loading, SHA-256 hashing, exact ``chars:start:end`` locators, mechanical
text handling, and atomic directory publication.

Pipeline position::

    source ingestion
        -> prepared canonical SourceDocument values
        -> automatic build / large-LLM curation / future corpus tools

Core intentionally knows nothing about individual websites, selection or
registry workflows, embedding models, LLM proposal schemas, CLI commands, or
runtime SQLite corpus semantics. Those responsibilities belong to higher-level
features or ``corpus-format``. Imports must remain side-effect free: core never
performs network access, model loading, or implicit generated-data writes.
"""

__version__ = "0.1.0"
