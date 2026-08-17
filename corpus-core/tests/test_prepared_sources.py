import json
from pathlib import Path

from sibyl_corpus_core.prepared_sources import load_prepared_sources


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
