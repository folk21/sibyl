"""Cross-source document-format parsers used during canonicalization.

A format parser extracts text structure from a raw representation without
owning source provenance, fallback policy, or network acquisition. Source
adapters decide when to use these parsers. Passage splitting, embeddings, and
corpus publication are outside this package."""
