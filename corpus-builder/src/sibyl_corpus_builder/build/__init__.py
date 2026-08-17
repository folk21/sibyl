"""Automatic corpus-build feature for generic local semantic retrieval.

The ``build`` feature consumes deterministic prepared canonical sources and
constructs the current runtime corpus used for open-ended user questions. It
performs mechanical passage extraction, creates retrieval hints, resolves and
caches embeddings, writes SQLite/vector/manifest artifacts, validates them, and
publishes the completed output atomically.

Pipeline position::

    prepared canonical SourceDocument values
        -> automatic passage splitter
        -> retrieval hints
        -> embeddings and cache
        -> corpus.db / vectors.json / manifest.json
        -> validation
        -> atomic publication

This path is deliberately independent from large-LLM literary curation and
remains the fallback for arbitrary questions. The public functions re-exported
here expose orchestration only; detailed splitter, embedding, persistence, and
runtime-model mechanics remain under ``build._internal``.
"""

from .api import build_corpus, inspect_passages, validate_corpus

__all__ = ["build_corpus", "inspect_passages", "validate_corpus"]
