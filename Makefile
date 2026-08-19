.PHONY: help check check-all test-mobile test-desktop build-runtime-corpus run-desktop run-desktop-real download-runtime-model test-corpus-core test-corpus-builder validate-format validate-sources smoke-corpus format-python

help:
	@echo "Sibyl repository targets:"
	@echo "  check                Run lightweight checks (no Android/model/network required)"
	@echo "  check-all            Run lightweight checks plus Android and desktop shared tests"
	@echo "  test-mobile          Run Android shared host tests"
	@echo "  test-desktop         Run shared plus Desktop runtime JVM tests"
	@echo "  build-runtime-corpus Build one runtime corpus from all locally prepared source sets"
	@echo "  run-desktop          Run the interactive Compose Desktop demo"
	@echo "  run-desktop-real     Run Desktop against a built local corpus (CORPUS_DIR/MODEL_DIR)"
	@echo "  download-runtime-model  Download the local ONNX/tokenizer bundle for real Desktop retrieval"
	@echo "  test-corpus-core     Run shared Python corpus-core tests"
	@echo "  test-corpus-builder  Run Python builder and structural regression tests"
	@echo "  validate-format      Validate corpus format fixtures"
	@echo "  validate-sources     Validate source registry records and collections"
	@echo "  smoke-corpus         Build and validate a temporary synthetic corpus"
	@echo "  format-python        Run Ruff formatting and lint fixes"

check: test-corpus-core test-corpus-builder validate-format validate-sources
	@echo "Lightweight repository checks passed."
	@echo "Run 'make check-all' on a workstation with JDK 17 and the Android toolchain configured."

check-all: check test-mobile test-desktop
	@echo "All configured repository tests passed."

test-mobile:
	cd mobile && ./gradlew :shared:testAndroidHostTest

test-desktop:
	cd mobile && ./gradlew :shared:desktopTest :desktopApp:jvmTest

run-desktop:
	cd mobile && ./gradlew :desktopApp:run

RUNTIME_CORPUS_DIR ?= corpus-builder/data/output
PREPARED_SOURCE_ROOT ?= corpus-builder/data/work
QUESTIONS_PATH ?= corpus-curation/questions.json
CURATION_ROOT ?= corpus-curation/curated
CORPUS_DIR ?= $(RUNTIME_CORPUS_DIR)
MODEL_DIR ?= corpus-builder/data/runtime-models/multilingual-e5-small

build-runtime-corpus:
	PYTHONPATH=corpus-core/src:corpus-builder/src python -m sibyl_corpus_builder.cli build-available \
		--config corpus-builder/config/real-text.toml \
		--source-root "$(PREPARED_SOURCE_ROOT)" \
		--questions "$(QUESTIONS_PATH)" \
		--curation-root "$(CURATION_ROOT)" \
		--output "$(RUNTIME_CORPUS_DIR)"

run-desktop-real:
	@test -f "$(CORPUS_DIR)/manifest.json" || (echo "Corpus manifest not found: $(CORPUS_DIR)/manifest.json" && exit 1)
	@test -f "$(MODEL_DIR)/model-manifest.json" || (echo "Runtime model manifest not found: $(MODEL_DIR)/model-manifest.json" && exit 1)
	cd mobile && SIBYL_CORPUS_DIR="$(abspath $(CORPUS_DIR))" SIBYL_MODEL_DIR="$(abspath $(MODEL_DIR))" ./gradlew :desktopApp:run

download-runtime-model:
	cd corpus-builder && PYTHONPATH=../corpus-core/src:src python -m sibyl_corpus_builder.cli download-runtime-model --config config/real-text.toml --output data/runtime-models/multilingual-e5-small

test-corpus-core:
	PYTHONPATH=corpus-core/src python -m pytest corpus-core/tests

test-corpus-builder:
	PYTHONPATH=corpus-core/src:corpus-builder/src python -m pytest corpus-builder/tests

validate-format:
	python corpus-format/tools/validate_schema.py

validate-sources:
	python corpus-sources/tools/validate_registry.py

smoke-corpus:
	@tmp_dir=$$(mktemp -d); \
	trap 'rm -rf "$$tmp_dir"' EXIT; \
	PYTHONPATH=corpus-core/src:corpus-builder/src python -m sibyl_corpus_builder.cli build \
		--config corpus-builder/config/example.toml \
		--source test-corpus/sources \
		--output "$$tmp_dir/output"; \
	PYTHONPATH=corpus-core/src:corpus-builder/src python -m sibyl_corpus_builder.cli validate \
		--corpus "$$tmp_dir/output/corpus.db"

format-python:
	python -m ruff check --fix corpus-core corpus-builder && python -m ruff format corpus-core corpus-builder
