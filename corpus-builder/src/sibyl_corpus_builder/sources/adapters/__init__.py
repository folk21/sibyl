"""Source-family adapters used by the source-ingestion feature.

Adapters isolate website- or repository-specific behavior from generic source
orchestration. Each source family keeps its discovery, fetch, and normalization
logic together so a developer can understand or extend one integration without
searching across unrelated global modules.

Current source-oriented packages include Lib.ru and Project Gutenberg. Shared
document formats that are not owned by one source family live under
``adapters.formats`` instead.

Adapters are implementation details of ``sources``. They may depend on
feature-neutral ``corpus-core`` primitives, but they must not know about the
automatic build pipeline, embeddings, LLM proposal formats, or runtime corpus
persistence. Explicit source-family dispatch is owned by
``sources._internal.adapters`` rather than automatic plugin discovery.
"""
