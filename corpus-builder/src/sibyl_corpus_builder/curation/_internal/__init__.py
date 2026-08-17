"""Private implementation layer for large-LLM curation.

Modules in this package implement the curation trust boundary behind
:mod:`sibyl_corpus_builder.curation.api`. They load and validate stable guided
questions, build deterministic export bundles, parse external model proposals,
resolve proposed character ranges against local canonical sources, verify
canonical/text hashes, and normalize the accepted mappings for Git-safe
storage.

The external LLM output is treated as an untrusted proposal. Validation here
must be deterministic and must reject stale source hashes, invalid locators,
unknown question IDs, or any mismatch between the proposed range and the local
canonical text.

Other features should not import this package. Shared exact-text primitives
belong in ``sibyl_corpus_core``; curation-specific proposal and question
semantics remain private here.
"""
