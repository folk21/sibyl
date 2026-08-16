# Corpus curation rules

Root `AGENTS.md` also applies.

`corpus-curation/` contains small Git-tracked product/curation metadata. It must never become a storage location for downloaded canonical books, generated corpus databases, model files, or large copied literary excerpts.

## Question catalog

- Question IDs are stable product identifiers. Do not rename an existing ID casually.
- User-facing prompt text may be in the catalog language; software documentation and metadata keys remain English.
- A semantic rewrite of the catalog requires a new `catalog_id` so existing curation mappings cannot silently change meaning.
- Keep question/state prompts broad enough to support multiple plausible literary answers rather than one expected quotation.

## LLM curation

- Large-model output is curation metadata, not authoritative literary text.
- Every selected passage must pin `work_id`, `text_version_id`, `canonical_sha256`, an exact `chars:start:end` locator, and `text_sha256`.
- Do not store the full selected passage in committed proposal/curated files. The local Python importer resolves and verifies the exact canonical slice.
- One passage may map to multiple question IDs, and one question should eventually map to multiple passages.
- Do not force coverage for every question when an author/work has no strong match.
- Curation strength expresses semantic/editorial fit, not vector cosine similarity.
- LLM proposals must pass local exact-text validation before they are treated as curated data.

See [`../docs/WORKFLOW.md`](../docs/WORKFLOW.md) for the end-to-end workflow.
