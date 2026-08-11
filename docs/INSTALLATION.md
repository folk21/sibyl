# Installation

Command examples use `/path/to/sibyl` as the repository root unless the clone command creates `sibyl` explicitly. Replace the placeholder with your actual checkout path.

Sibyl is a monorepo with independently buildable mobile and corpus-tooling projects. There is no backend prerequisite.

## Minimal prerequisites

For repository validation and corpus tooling:

- Git;
- Python 3.11+.

For the Desktop development harness:

- JDK 17+.

For Android development:

- JDK 17+;
- Android Studio;
- Android SDK 36.

## First checkout

```bash
git clone <repository-url> sibyl
cd sibyl
python -m venv .venv
source .venv/bin/activate
python -m pip install -e 'corpus-builder[dev]'
make check
```

`make check` does not require Android tooling, production models, or downloaded literature. See [`TESTS.md`](TESTS.md).

## Corpus builder development environment

```bash
cd /path/to/sibyl/corpus-builder
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

On Windows use `.venv\\Scripts\\activate`.

## Desktop development harness

From the repository root:

```bash
make run-desktop
```

This runs a JVM Compose Desktop application using the same shared UI/runtime code as Android. No Xcode, iOS simulator, REST server, or backend is required.

On Intel macOS, treat the Desktop harness as development-only/best-effort: the project uses JVM Desktop (not Kotlin/Native), but the current Compose Multiplatform 1.11.1 support matrix officially lists macOS arm64. Re-run `make run-desktop` after Compose/Skiko upgrades to catch host compatibility changes.

## Android

```bash
cd /path/to/sibyl/mobile
./gradlew :androidApp:assembleDebug
```

The first Gradle invocation may download the configured distribution/dependencies when they are not cached.

## Production assets

Do not add production literary archives, ONNX models, embeddings, ANN indexes, generated translations, or builder work directories to Git. They will be built/downloaded separately once production adapters exist.
