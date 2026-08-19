"""Private implementation of build-time curated-passage machine translation.

Modules here derive deterministic translation bundles from public curation
contracts, validate external large-LLM output without rewriting it, and preserve
provider/model/source hashes for later corpus assembly. Other builder features
must depend only on ``translation.api`` rather than these internals.
"""
