"""Feature-neutral canonical-source contracts and deterministic primitives.

``sibyl_corpus_core`` owns ``SourceDocument``, prepared-source loading, exact
hashing/character locators, small mechanical text helpers, and atomic directory
publication shared by independent corpus features. It knows nothing about
source sites, embedding models, LLM proposal schemas, or persisted runtime
corpus semantics, and its imports remain side-effect free."""

__version__ = "0.1.0"
