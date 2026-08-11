# Mobile development rules

Root `AGENTS.md` also applies.

## Scope

`mobile/` owns local question processing, candidate selection, display, history, saved encounters, and platform application entry points.

## Boundaries

- `shared` owns reusable Kotlin domain/retrieval/selection/state/shared Compose UI.
- `androidApp` owns the Android product entry point and Android-only integration.
- `desktopApp` is a JVM development harness for fast interactive validation on a workstation. It must reuse shared UI/runtime code and must not introduce a local REST/backend layer.
- iOS is deferred. Do not add/configure iOS targets unless the project explicitly resumes iOS development.
- Common code must not import Android/desktop platform APIs.
- ONNX Runtime and ANN/index APIs must stay behind `EmbeddingEngine`/`VectorIndex`-style interfaces.
- UI must not implement retrieval ranking or corpus parsing.

## Selection behavior

- Never replace controlled random sampling with top-1 retrieval.
- Keep semantic relevance as a minimum gate/weight.
- Inject randomness for deterministic tests.
- Repetition is allowed; recency may reduce weight.
- Length preference selects prepared variants and never truncates stored literary text.

## Answer integrity

- Display exact stored passage text in core mode.
- Distinguish original, human translation, and machine translation.
- Machine translation must be visibly labelled.
- Source details should be available without forcing metadata to precede the reading experience.

## Privacy

- Core retrieval must not require network access.
- Desktop development must preserve the same local-first boundary as Android unless an explicit development adapter is documented.
- Do not log user questions/encounters externally or in production logs.

## Development loop

From the repository root, use the desktop harness for manual iteration:

```bash
make run-desktop
```

Run focused Gradle tests from `mobile/`:

```bash
cd /path/to/sibyl/mobile
./gradlew :shared:testAndroidHostTest
./gradlew :shared:desktopTest
```

Build Android from `mobile/` when platform integration changes:

```bash
cd /path/to/sibyl/mobile
./gradlew :androidApp:assembleDebug
```

Use root `docs/TESTS.md` and `docs/ARCHITECTURE.md` for detailed repository policy.
