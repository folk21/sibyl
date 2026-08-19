import json
from pathlib import Path

from sibyl_corpus_core.prepared_sources import load_prepared_sources, load_prepared_source_sets


def test_load_prepared_sources_normalizes_only_newlines(tmp_path: Path) -> None:
    (tmp_path / "fixture.txt").write_text("First\r\n\r\nSecond  line.\r\n", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "works": [
                    {
                        "id": "fixture",
                        "author": "Fixture",
                        "title": "Fixture Work",
                        "file": "fixture.txt",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    document = load_prepared_sources(tmp_path)[0]

    assert document.text == "First\n\nSecond  line.\n"


def _write_prepared(path: Path, *, work_id: str, version_id: str, author: str = "Author") -> None:
    path.mkdir()
    file_name = f"{version_id}.txt"
    (path / file_name).write_text(f"Text for {work_id}/{version_id}.\n", encoding="utf-8")
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "works": [
                    {
                        "id": work_id,
                        "text_version_id": version_id,
                        "author": author,
                        "title": f"Work {work_id}",
                        "file": file_name,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_load_prepared_source_sets_composes_independent_directories(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_prepared(first, work_id="b-work", version_id="b-v1")
    _write_prepared(second, work_id="a-work", version_id="a-v1")

    documents = load_prepared_source_sets([first, second])

    assert [(item.source_id, item.text_version_id) for item in documents] == [
        ("b-work", "b-v1"),
        ("a-work", "a-v1"),
    ]


def test_load_prepared_source_sets_rejects_duplicate_text_versions(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_prepared(first, work_id="same-work", version_id="same-v1")
    _write_prepared(second, work_id="same-work", version_id="same-v1")

    try:
        load_prepared_source_sets([first, second])
    except ValueError as error:
        assert "Duplicate prepared text version" in str(error)
    else:
        raise AssertionError("Expected duplicate prepared text version to be rejected")


def test_load_prepared_source_sets_rejects_conflicting_work_identity(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_prepared(first, work_id="same-work", version_id="v1", author="First Author")
    _write_prepared(second, work_id="same-work", version_id="v2", author="Other Author")

    try:
        load_prepared_source_sets([first, second])
    except ValueError as error:
        assert "Conflicting prepared work identity" in str(error)
    else:
        raise AssertionError("Expected conflicting prepared work identity to be rejected")
