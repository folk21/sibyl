import json
import sqlite3
from pathlib import Path

from sibyl_corpus_builder.builder import build_corpus
from sibyl_corpus_builder.config import load_config
from sibyl_corpus_builder.validation import validate_corpus


def test_builder_creates_valid_artifacts(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "fixture.txt").write_text(
        "The first paragraph contains enough words to become a passage candidate.\n\n"
        "The second paragraph also contains enough words to remain useful and complete.",
        encoding="utf-8",
    )
    (source_dir / "manifest.json").write_text(
        json.dumps(
            {
                "works": [
                    {
                        "id": "fixture",
                        "author": "Synthetic fixture",
                        "title": "Fixture work",
                        "file": "fixture.txt",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[corpus]
format_version = 3
language = "en"
[passages]
min_words = 5
preferred_words = 10
max_words = 40
overlap_paragraphs = 0
[hints]
hints_per_passage = 2
[embeddings]
provider = "hash"
dimensions = 8
normalize = true
""".strip(),
        encoding="utf-8",
    )

    output = tmp_path / "output"
    build_corpus(load_config(config_path), source_dir, output)
    validate_corpus(output / "corpus.db")

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format_version"] == 3
    assert manifest["counts"]["passages"] >= 1

    with sqlite3.connect(output / "corpus.db") as connection:
        text = connection.execute("SELECT text FROM passage_text LIMIT 1").fetchone()[0]
    assert "first paragraph" in text.lower()
