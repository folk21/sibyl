import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from sibyl_corpus_builder.build.api import build_corpus
from sibyl_corpus_builder.build.config import load_config
from sibyl_corpus_builder.curation import import_curation


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prepared_source(path: Path) -> str:
    path.mkdir()
    text = (
        "The first synthetic paragraph considers whether a familiar life should continue.\n\n"
        "The second synthetic paragraph accepts uncertainty and chooses a different road.\n\n"
        "The third synthetic paragraph remembers that doubt can return after a decision.\n"
    )
    (path / "fixture-v1.txt").write_text(text, encoding="utf-8")
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "works": [
                    {
                        "id": "fixture-work",
                        "text_version_id": "fixture-v1",
                        "author": "Fixture Author",
                        "title": "Fixture Work",
                        "file": "fixture-v1.txt",
                        "source_name": "Fixture Source",
                        "language": "en",
                        "original_language": "en",
                        "category": "literature",
                        "text_role": "original",
                        "rights_status": "approved",
                        "canonical_text_sha256": _sha256(text),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return text


def _questions(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_id": "fixture-guided-v1",
                "language": "en",
                "items": [
                    {
                        "id": "change",
                        "kind": "question",
                        "theme": "change",
                        "text": "When should I change?",
                    },
                    {
                        "id": "unused",
                        "kind": "state",
                        "theme": "uncertainty",
                        "text": "Nothing feels clear.",
                    },
                    {
                        "id": "doubt",
                        "kind": "question",
                        "theme": "uncertainty",
                        "text": "Why does doubt return?",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _config(path: Path) -> None:
    path.write_text(
        """
[corpus]
format_version = 4
language = "en"
[passages]
min_words = 5
preferred_words = 10
max_words = 40
overlap_paragraphs = 0
[hints]
provider = "deterministic"
hints_per_passage = 1
[embeddings]
provider = "hash"
dimensions = 8
normalize = true
query_prefix = "query: "
""".strip(),
        encoding="utf-8",
    )


def _curation(source: Path, questions: Path, canonical: str, output: Path) -> tuple[str, str]:
    first = "The first synthetic paragraph considers whether a familiar life should continue."
    second = "The second synthetic paragraph accepts uncertainty and chooses a different road."
    passages = []
    for selected, matches in [
        (first, [{"question_id": "change", "strength": 0.91}]),
        (
            second,
            [
                {"question_id": "change", "strength": 0.55},
                {"question_id": "doubt", "strength": 0.12},
            ],
        ),
    ]:
        start = canonical.index(selected)
        end = start + len(selected)
        passages.append(
            {
                "work_id": "fixture-work",
                "text_version_id": "fixture-v1",
                "canonical_sha256": _sha256(canonical),
                "source_locator": f"chars:{start}:{end}",
                "text_sha256": _sha256(selected),
                "matches": matches,
            }
        )

    proposal = output.with_name("proposal.json")
    proposal.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "proposal_id": "fixture-curation-v1",
                "question_catalog_id": "fixture-guided-v1",
                "curation_method": "large_llm",
                "source_bundle_id": "cb_0123456789abcdefabcd",
                "passages": passages,
            }
        ),
        encoding="utf-8",
    )
    import_curation(
        source_dir=source,
        questions_path=questions,
        input_path=proposal,
        output_path=output,
    )
    return first, second


def test_build_materializes_exact_curated_passages_and_guided_mappings(tmp_path: Path) -> None:
    source = tmp_path / "source"
    canonical = _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)
    curated = tmp_path / "curated.json"
    expected_first, expected_second = _curation(source, questions, canonical, curated)
    config_path = tmp_path / "config.toml"
    _config(config_path)
    output = tmp_path / "output"

    build_corpus(
        load_config(config_path),
        source,
        output,
        questions_path=questions,
        curation_paths=[curated],
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format_version"] == 4
    assert manifest["counts"]["guided_questions"] == 3
    assert manifest["counts"]["guided_mappings"] == 3

    with sqlite3.connect(output / "corpus.db") as connection:
        question_rows = connection.execute(
            "SELECT id, ordinal FROM guided_question ORDER BY ordinal"
        ).fetchall()
        assert question_rows == [("change", 0), ("unused", 1), ("doubt", 2)]
        mappings = connection.execute(
            "SELECT question_id, strength FROM guided_question_passage "
            "ORDER BY question_id, strength"
        ).fetchall()
        assert mappings == [("change", 0.55), ("change", 0.91), ("doubt", 0.12)]
        curated_texts = [
            row[0]
            for row in connection.execute(
                "SELECT pt.text FROM passage_text pt JOIN passage p ON p.id = pt.passage_id "
                "WHERE p.id LIKE 'cp_%' ORDER BY p.source_locator"
            ).fetchall()
        ]
        assert curated_texts == [expected_first, expected_second]


def test_build_with_questions_only_persists_catalog_without_mappings(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)
    config_path = tmp_path / "config.toml"
    _config(config_path)
    output = tmp_path / "output"

    build_corpus(
        load_config(config_path),
        source,
        output,
        questions_path=questions,
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["guided_questions"] == 3
    assert manifest["counts"]["guided_mappings"] == 0
    with sqlite3.connect(output / "corpus.db") as connection:
        rows = connection.execute(
            "SELECT id, ordinal FROM guided_question ORDER BY ordinal"
        ).fetchall()
        assert rows == [("change", 0), ("unused", 1), ("doubt", 2)]
        assert connection.execute(
            "SELECT COUNT(*) FROM guided_question_passage"
        ).fetchone()[0] == 0


def test_build_without_curation_publishes_valid_v4_free_form_corpus(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _prepared_source(source)
    config_path = tmp_path / "config.toml"
    _config(config_path)
    output = tmp_path / "output"

    build_corpus(load_config(config_path), source, output)

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format_version"] == 4
    assert manifest["counts"]["guided_questions"] == 0
    assert manifest["counts"]["guided_mappings"] == 0
    with sqlite3.connect(output / "corpus.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM guided_question").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM guided_question_passage").fetchone()[0] == 0


def test_build_requires_questions_for_curation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    canonical = _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)
    curated = tmp_path / "curated.json"
    _curation(source, questions, canonical, curated)
    config_path = tmp_path / "config.toml"
    _config(config_path)

    with pytest.raises(ValueError, match="--questions is required"):
        build_corpus(
            load_config(config_path),
            source,
            tmp_path / "output",
            curation_paths=[curated],
        )


def test_build_rejects_duplicate_curated_passages_across_inputs(tmp_path: Path) -> None:
    source = tmp_path / "source"
    canonical = _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)
    curated = tmp_path / "curated.json"
    _curation(source, questions, canonical, curated)
    config_path = tmp_path / "config.toml"
    _config(config_path)

    with pytest.raises(ValueError, match="Duplicate curated passage_id"):
        build_corpus(
            load_config(config_path),
            source,
            tmp_path / "output",
            questions_path=questions,
            curation_paths=[curated, curated],
        )


def test_stale_curated_hash_blocks_atomic_publication(tmp_path: Path) -> None:
    source = tmp_path / "source"
    canonical = _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)
    curated = tmp_path / "curated.json"
    _curation(source, questions, canonical, curated)
    config_path = tmp_path / "config.toml"
    _config(config_path)

    source_file = source / "fixture-v1.txt"
    source_file.write_text(canonical + "Changed after curation.\n", encoding="utf-8")
    output = tmp_path / "output"

    with pytest.raises(ValueError, match="canonical SHA-256"):
        build_corpus(
            load_config(config_path),
            source,
            output,
            questions_path=questions,
            curation_paths=[curated],
        )
    assert not output.exists()
