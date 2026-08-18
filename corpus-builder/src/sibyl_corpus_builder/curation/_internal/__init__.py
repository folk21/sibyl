"""Private implementation of the large-LLM curation trust boundary.

Modules here load guided questions, build deterministic export bundles, parse
untrusted proposals, and verify exact canonical ranges/hashes before producing
Git-safe metadata. Shared exact-text primitives belong in ``corpus-core``;
other builder features must not depend on this private package."""
