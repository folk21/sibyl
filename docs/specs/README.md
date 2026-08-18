# Change specifications

`docs/specs/` contains specifications for significant planned or in-progress changes to Sibyl. A spec describes the intended delta from the current system before implementation; it is **not** canonical documentation of what the repository already does.

Current product and implementation truth remains in the owning documents such as `CONCEPT.md`, `ARCHITECTURE.md`, `IMPLEMENTATION.md`, `CORPUS_FORMAT.md`, `SOURCES.md`, and `WORKFLOW.md`.

## When to create a spec

Create an active spec when a change is cross-cutting, alters a persisted/public contract, introduces a substantial P0/P1 capability, or is large enough that requirements and validation need to survive across implementation sessions. Small bug fixes, local refactors, routine documentation maintenance, and narrow implementation tasks do not require a spec.

## Lifecycle

1. Create `docs/specs/active/<change>.md` before implementation.
2. Define the goal, current state, requirements, scenarios, non-goals, design constraints, compatibility impact, validation, and implementation tasks.
3. Treat requirements/scenarios as the source for acceptance tests. Tests remain normal maintained source code rather than generated disposable artifacts.
4. Implement the change while preserving current repository invariants and the nearest `AGENTS.md` rules.
5. After the implementation is accepted, update the owning current-state documents and roadmap/history entries.
6. Move the completed spec to `docs/specs/archive/`. Archived specs are historical design intent, not current system documentation.

Active specs are normal LLM/project context. `concat_sibyl.sh` excludes `docs/specs/archive/` so completed design history does not crowd routine coding context; full repository archives keep it.

## Spec template

Use this structure as a default and omit sections that genuinely do not apply:

```text
# <Change name>

Status / roadmap links

## Goal
## Current state
## Requirements
## Scenarios
## Non-goals
## Design
## Compatibility / migration
## Validation
## Implementation tasks
```

Requirements should have stable IDs such as `R1`, and scenarios should reference the requirements they exercise. The `Validation` section should map requirements/scenarios to automated tests or, when automation is not practical, to an explicit manual check.

## Active specs

- [`active/guided-question-runtime.md`](active/guided-question-runtime.md) — publish validated curated mappings into runtime corpus format and expose guided-question selection in Desktop while preserving free-form retrieval.
