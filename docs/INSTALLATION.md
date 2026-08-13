# Installation

Command examples use `/path/to/sibyl` as the repository root unless the clone command creates `sibyl` explicitly. Replace the placeholder with your actual checkout path.

Sibyl is a monorepo with independently buildable mobile and corpus-tooling projects. There is no backend prerequisite.

## Minimal prerequisites

For repository validation and non-ML corpus tooling:

- Git;
- Python 3.11+.

For the optional Sentence Transformers embedding environment:

- Python 3.11 or 3.12.

The ML extra is intentionally pinned to a conservative stack that remains usable on Intel macOS. Do not install `.[ml]` from Python 3.13+; create a separate Python 3.11/3.12 virtual environment instead.

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

### Optional ML environment

The regular builder can use Python 3.11+, but the current embedding toolchain is pinned for Python 3.11/3.12 so it remains reproducible on Intel macOS.

If your normal Python is newer, create a separate ML environment. For example on macOS with Python 3.12 installed:

```bash
cd /path/to/sibyl/corpus-builder
python3.12 -m venv .venv-ml
source .venv-ml/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[ml]'
```

The current pinned ML stack is `numpy==1.26.4`, `torch==2.2.2`, and `sentence-transformers==3.4.1`. Keep these versions aligned unless a dependency upgrade is deliberately tested on all supported corpus-building hosts.

## Desktop development harness

From the repository root:

```bash
make run-desktop
```

This runs a JVM Compose Desktop application using the same shared UI/runtime code as Android. No Xcode, iOS simulator, REST server, or backend is required. Demo mode requires no model assets. Real-corpus mode additionally uses the JVM ONNX Runtime, a local Hugging Face tokenizer, and SQLite JDBC dependencies resolved by Gradle.

On Intel macOS, treat the Desktop harness as development-only/best-effort: the project uses JVM Desktop (not Kotlin/Native), but the current Compose Multiplatform 1.11.1 support matrix officially lists macOS arm64. Re-run `make run-desktop` after Compose/Skiko upgrades to catch host compatibility changes.

## Android

```bash
cd /path/to/sibyl/mobile
./gradlew :androidApp:assembleDebug
```

The first Gradle invocation may download the configured distribution/dependencies when they are not cached.

## Runtime development assets

The real Desktop harness expects a built corpus directory and a matching runtime model bundle. Generate them under ignored `corpus-builder/data/` paths:

```bash
cd /path/to/sibyl/corpus-builder
sibyl-corpus download-runtime-model \
  --config config/real-text.toml \
  --output data/runtime-models/multilingual-e5-small
```

Do not add literary archives, ONNX models, embeddings, generated corpus databases, generated translations, ANN indexes, or builder work directories to Git. They remain local/generated assets and are also excluded from shareable project archives.
