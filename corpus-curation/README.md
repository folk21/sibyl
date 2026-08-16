# Sibyl corpus curation

This directory stores small Git-tracked metadata for LLM-assisted literary curation. It does not store downloaded source texts or published runtime corpus artifacts.

- `questions.json` — versioned catalog of 48 guided user questions/states.
- `proposals/` — LLM-generated locator/hash mappings awaiting local import/validation.
- `curated/` — normalized mappings that have passed the local importer against a concrete prepared canonical source.

The full workflow, including how to prepare an author, export a local curation bundle, ask a large LLM for a patch, and validate that patch locally, is documented in [`../docs/WORKFLOW.md`](../docs/WORKFLOW.md).
