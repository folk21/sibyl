# Sibyl applications

`mobile/` contains the shared Kotlin Multiplatform runtime/UI plus the current application hosts:

- `shared/` — domain models, retrieval contracts/orchestration, selection, demo retrieval, shared Compose UI, and common tests;
- `androidApp/` — Android product host;
- `desktopApp/` — JVM development host and current real-corpus runtime adapters.

The Desktop host exists for rapid local iteration and does not introduce a REST/backend boundary.

## Run Desktop

From the repository root, synthetic demo mode:

```bash
make run-desktop
```

Real local corpus mode:

```bash
make run-desktop-real
```

The default real mode expects the current assembled corpus at `corpus-builder/data/output` and a model bundle at `corpus-builder/data/runtime-models/multilingual-e5-small`. Override with `CORPUS_DIR=... MODEL_DIR=...`. Format-v4 corpora built with guided mappings expose a guided-question dropdown; format-v3 corpora remain free-form-only.

On Intel macOS, real mode may also require the locally built DJL tokenizer native library through `RUST_LIBRARY_PATH`; see [`../docs/INSTALLATION.md`](../docs/INSTALLATION.md).

## Tests

From `mobile/`:

```bash
./gradlew :shared:testAndroidHostTest
./gradlew :shared:desktopTest
./gradlew :desktopApp:jvmTest
```

From the repository root, use `make check-all` when the Android toolchain is configured.

## Android validation

```bash
cd mobile
./gradlew :androidApp:assembleDebug
```

Android currently hosts the shared demo retrieval path. Real Android ONNX/index/storage adapters are still future work.

## Read next

- [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — current modules, classes, Desktop adapters, libraries, and request flow.
- [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) — stable system boundaries.
- [`../docs/TESTS.md`](../docs/TESTS.md) — repository test matrix.
- [`AGENTS.md`](AGENTS.md) — local development rules.
