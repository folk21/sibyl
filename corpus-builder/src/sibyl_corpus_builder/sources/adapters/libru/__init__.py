"""Lib.ru discovery, resilient acquisition, and canonicalization adapter.

It owns author-page classification, ordered ``TXT -> HTML -> FB2`` source
candidates, and versioned Lib.ru normalization that preserves literary wording.
Malformed candidates may fall through to the next representation. Selection
persistence, registry approval, embeddings, and LLM curation belong to other
layers."""
