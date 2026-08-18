"""Automatic corpus-build feature for generic local semantic retrieval.

It consumes prepared canonical sources and owns mechanical passage extraction,
retrieval text, embeddings/cache, runtime artifact writing, validation, and
atomic publication. Large-LLM literary curation is a separate feature; callers
should use this package's public API rather than ``build._internal``."""

from .api import build_corpus, inspect_passages, validate_corpus

__all__ = ["build_corpus", "inspect_passages", "validate_corpus"]
