"""Source-family adapters used by source ingestion.

Adapters isolate source-specific discovery, fetch, and normalization behavior;
shared document formats live under ``adapters.formats``. They may use
feature-neutral ``corpus-core`` primitives but must not know about embeddings,
LLM proposal formats, or runtime corpus persistence."""
