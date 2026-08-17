import hashlib
import json
from pathlib import Path

from sibyl_corpus_builder.sources.api import import_registry_source, prepare_registry_sources


def _write_registry(root: Path) -> None:
    works = root / "works"
    works.mkdir(parents=True)
    (works / "fixture.toml").write_text(
        """schema_version = 1
work_id = "fixture"
author = "Fixture Author"
title = "Fixture Work"
category = "literature"
original_language = "ru"
enabled = false
review_status = "candidate"
russian_display_policy = "source_text"

[[text_versions]]
id = "fixture-v1"
language = "ru"
role = "original"
source_family = "russian_wikisource"
source_name = "Fixture Source"
source_uri = "https://example.invalid/fixture"
source_locator = "candidate"
rights_status = "review_required"
rights_jurisdiction = "RU"
provenance = "Fixture provenance"
""",
        encoding="utf-8",
    )


def test_import_and_prepare_preserve_canonical_text_and_hashes(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    _write_registry(registry)
    source = tmp_path / "source.txt"
    source.write_text("Первый абзац.\r\n\r\nВторой абзац.\r\n", encoding="utf-8")
    cache = tmp_path / "cache"

    import_registry_source(
        registry_dir=registry,
        cache_dir=cache,
        work_id="fixture",
        version_id=None,
        file_path=source,
        allow_unapproved=True,
    )

    prepared = tmp_path / "prepared"
    prepare_registry_sources(
        registry_dir=registry,
        cache_dir=cache,
        work_ids=["fixture"],
        output_dir=prepared,
        allow_unapproved=True,
    )

    canonical = (prepared / "fixture-v1.txt").read_text(encoding="utf-8")
    assert canonical == "Первый абзац.\n\nВторой абзац.\n"
    manifest = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
    entry = manifest["works"][0]
    assert entry["canonical_text_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert entry["rights_status"] == "review_required"
