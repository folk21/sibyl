.PHONY: help check check-all test-mobile test-desktop run-desktop test-corpus-builder validate-format validate-sources smoke-corpus format-python

help:
	@echo "Sibyl repository targets:"
	@echo "  check                Run lightweight checks (no Android/model/network required)"
	@echo "  check-all            Run lightweight checks plus Android and desktop shared tests"
	@echo "  test-mobile          Run Android shared host tests"
	@echo "  test-desktop         Run shared tests on the desktop JVM target"
	@echo "  run-desktop          Run the interactive Compose Desktop development app"
	@echo "  test-corpus-builder  Run Python builder tests"
	@echo "  validate-format      Validate corpus format fixtures"
	@echo "  validate-sources     Validate source registry records and collections"
	@echo "  smoke-corpus         Build and validate a temporary synthetic corpus"
	@echo "  format-python        Run Ruff formatting and lint fixes"

check: test-corpus-builder validate-format validate-sources
	@echo "Lightweight repository checks passed."
	@echo "Run 'make check-all' on a workstation with JDK 17 and the Android toolchain configured."

check-all: check test-mobile test-desktop
	@echo "All configured repository tests passed."

test-mobile:
	cd mobile && ./gradlew :shared:testAndroidHostTest

test-desktop:
	cd mobile && ./gradlew :shared:desktopTest

run-desktop:
	cd mobile && ./gradlew :desktopApp:run

test-corpus-builder:
	cd corpus-builder && PYTHONPATH=src python -m pytest

validate-format:
	python corpus-format/tools/validate_schema.py

validate-sources:
	python corpus-sources/tools/validate_registry.py

smoke-corpus:
	@tmp_dir=$$(mktemp -d); \
	trap 'rm -rf "$$tmp_dir"' EXIT; \
	PYTHONPATH=corpus-builder/src python -m sibyl_corpus_builder.cli build \
		--config corpus-builder/config/example.toml \
		--source test-corpus/sources \
		--output "$$tmp_dir/output"; \
	PYTHONPATH=corpus-builder/src python -m sibyl_corpus_builder.cli validate \
		--corpus "$$tmp_dir/output/corpus.db"

format-python:
	cd corpus-builder && python -m ruff check --fix . && python -m ruff format .
