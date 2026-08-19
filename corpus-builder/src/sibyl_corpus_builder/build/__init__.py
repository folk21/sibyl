"""Runtime corpus-build feature for free-form retrieval and guided curation assembly.

It consumes prepared canonical sources and owns mechanical passage extraction,
retrieval text, embeddings/cache, format-v4 artifact writing, validation, and
atomic publication. Validated large-LLM curation remains owned by the separate
``curation`` feature; this build feature consumes only its public exact-slice
contract and never imports ``curation._internal``.
"""

from .api import build_corpus, inspect_passages, validate_corpus

__all__ = ["build_corpus", "inspect_passages", "validate_corpus"]
