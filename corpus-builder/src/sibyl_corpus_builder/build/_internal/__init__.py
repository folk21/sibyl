"""Private implementation of the automatic build feature.

Modules here implement splitting, hints, embedding/cache mechanics, runtime
artifact persistence, validation, and runtime-model bundle support behind
``build.api``. These contracts are build-specific, not ``corpus-core`` API, and
other features must not import this package directly."""
