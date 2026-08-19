import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from sibyl_corpus_builder.build.api import build_available_corpus, build_corpus
from sibyl_corpus_builder.build.config import load_config
from sibyl_corpus_builder.cli import build_parser
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



def _named_prepared_source(
    path: Path,
    *,
    work_id: str,
    version_id: str,
    author: str,
    title: str,
    text: str,
) -> str:
    path.mkdir()
    file_name = f"{version_id}.txt"
    (path / file_name).write_text(text, encoding="utf-8")
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "works": [
                    {
                        "id": work_id,
                        "text_version_id": version_id,
                        "author": author,
                        "title": title,
                        "file": file_name,
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


def _single_named_curation(
    *,
    source: Path,
    questions: Path,
    output: Path,
    proposal_id: str,
    work_id: str,
    version_id: str,
    canonical: str,
    selected: str,
    strength: float,
) -> None:
    start = canonical.index(selected)
    end = start + len(selected)
    proposal = output.with_name(f"{proposal_id}.json")
    proposal.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "proposal_id": proposal_id,
                "question_catalog_id": "fixture-guided-v1",
                "curation_method": "large_llm",
                "source_bundle_id": "cb_0123456789abcdefabcd",
                "passages": [
                    {
                        "work_id": work_id,
                        "text_version_id": version_id,
                        "canonical_sha256": _sha256(canonical),
                        "source_locator": f"chars:{start}:{end}",
                        "text_sha256": _sha256(selected),
                        "matches": [{"question_id": "change", "strength": strength}],
                    }
                ],
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


def test_build_composes_multiple_prepared_sources_and_curations(tmp_path: Path) -> None:
    first_source = tmp_path / "tolstoy"
    first_text = (
        "A first author considers a difficult change and chooses to act despite uncertainty.\n"
    )
    _named_prepared_source(
        first_source,
        work_id="tolstoy-work",
        version_id="tolstoy-v1",
        author="First Author",
        title="First Work",
        text=first_text,
    )
    second_source = tmp_path / "dostoevsky"
    second_text = (
        "A second author faces the same question from a different moral and emotional angle.\n"
    )
    _named_prepared_source(
        second_source,
        work_id="dostoevsky-work",
        version_id="dostoevsky-v1",
        author="Second Author",
        title="Second Work",
        text=second_text,
    )
    questions = tmp_path / "questions.json"
    _questions(questions)
    first_curated = tmp_path / "tolstoy-curated.json"
    second_curated = tmp_path / "dostoevsky-curated.json"
    _single_named_curation(
        source=first_source,
        questions=questions,
        output=first_curated,
        proposal_id="tolstoy-curation-v1",
        work_id="tolstoy-work",
        version_id="tolstoy-v1",
        canonical=first_text,
        selected=first_text.strip(),
        strength=0.9,
    )
    _single_named_curation(
        source=second_source,
        questions=questions,
        output=second_curated,
        proposal_id="dostoevsky-curation-v1",
        work_id="dostoevsky-work",
        version_id="dostoevsky-v1",
        canonical=second_text,
        selected=second_text.strip(),
        strength=0.8,
    )
    config_path = tmp_path / "config.toml"
    _config(config_path)
    output = tmp_path / "output"

    build_corpus(
        load_config(config_path),
        [first_source, second_source],
        output,
        questions_path=questions,
        curation_paths=[first_curated, second_curated],
    )

    with sqlite3.connect(output / "corpus.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM work").fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM guided_question_passage WHERE question_id = 'change'"
        ).fetchone()[0] == 2
        curated_authors = connection.execute(
            "SELECT DISTINCT a.display_name "
            "FROM guided_question_passage gqp "
            "JOIN passage p ON p.id = gqp.passage_id "
            "JOIN work w ON w.id = p.work_id "
            "JOIN author a ON a.id = w.author_id "
            "ORDER BY a.display_name"
        ).fetchall()
        assert curated_authors == [("First Author",), ("Second Author",)]


def test_build_cli_accepts_repeatable_sources() -> None:
    args = build_parser().parse_args(
        [
            "build",
            "--config",
            "config.toml",
            "--source",
            "first",
            "--source",
            "second",
            "--output",
            "output",
        ]
    )

    assert args.source == [Path("first"), Path("second")]



def test_build_available_discovers_prepared_sources_and_matching_curations(tmp_path: Path) -> None:
    source_root = tmp_path / "work"
    source_root.mkdir()
    first_source = source_root / "dostoevsky"
    first_text = "A first available author considers change and moral responsibility carefully.\n"
    _named_prepared_source(
        first_source,
        work_id="dostoevsky-work",
        version_id="dostoevsky-v1",
        author="First Available Author",
        title="First Available Work",
        text=first_text,
    )
    second_source = source_root / "tolstoy"
    second_text = "A second available author considers change from another human perspective.\n"
    _named_prepared_source(
        second_source,
        work_id="tolstoy-work",
        version_id="tolstoy-v1",
        author="Second Available Author",
        title="Second Available Work",
        text=second_text,
    )
    ignored_directory = source_root / "unfinished-download"
    ignored_directory.mkdir()
    (ignored_directory / "raw.txt").write_text("Not prepared yet", encoding="utf-8")

    questions = tmp_path / "questions.json"
    _questions(questions)
    curation_root = tmp_path / "curated"
    curation_root.mkdir()
    _single_named_curation(
        source=first_source,
        questions=questions,
        output=curation_root / "dostoevsky-v1.json",
        proposal_id="dostoevsky-curation-v1",
        work_id="dostoevsky-work",
        version_id="dostoevsky-v1",
        canonical=first_text,
        selected=first_text.strip(),
        strength=0.9,
    )
    (curation_root / "dostoevsky-curation-v1.json").unlink()
    _single_named_curation(
        source=second_source,
        questions=questions,
        output=curation_root / "tolstoy-v1.json",
        proposal_id="tolstoy-curation-v1",
        work_id="tolstoy-work",
        version_id="tolstoy-v1",
        canonical=second_text,
        selected=second_text.strip(),
        strength=0.8,
    )
    (curation_root / "tolstoy-curation-v1.json").unlink()

    unavailable_source = tmp_path / "chekhov"
    unavailable_text = "An unavailable prepared source has not been installed under the work root.\n"
    _named_prepared_source(
        unavailable_source,
        work_id="chekhov-work",
        version_id="chekhov-v1",
        author="Unavailable Author",
        title="Unavailable Work",
        text=unavailable_text,
    )
    _single_named_curation(
        source=unavailable_source,
        questions=questions,
        output=curation_root / "chekhov-v1.json",
        proposal_id="chekhov-curation-v1",
        work_id="chekhov-work",
        version_id="chekhov-v1",
        canonical=unavailable_text,
        selected=unavailable_text.strip(),
        strength=0.7,
    )
    (curation_root / "chekhov-curation-v1.json").unlink()

    config_path = tmp_path / "config.toml"
    _config(config_path)
    output = tmp_path / "output"
    build_available_corpus(
        load_config(config_path),
        source_root,
        output,
        questions_path=questions,
        curation_root=curation_root,
    )

    with sqlite3.connect(output / "corpus.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM work").fetchone()[0] == 2
        assert connection.execute(
            "SELECT COUNT(*) FROM guided_question_passage WHERE question_id = 'change'"
        ).fetchone()[0] == 2
        authors = connection.execute(
            "SELECT display_name FROM author ORDER BY display_name"
        ).fetchall()
        assert authors == [("First Available Author",), ("Second Available Author",)]


def test_build_available_cli_uses_roots_instead_of_explicit_author_lists() -> None:
    args = build_parser().parse_args(
        [
            "build-available",
            "--config",
            "config.toml",
            "--source-root",
            "data/work",
            "--questions",
            "questions.json",
            "--curation-root",
            "curated",
            "--output",
            "data/output",
        ]
    )

    assert args.source_root == Path("data/work")
    assert args.curation_root == Path("curated")
    assert args.output == Path("data/output")


def test_build_available_rejects_partially_available_curation(tmp_path: Path) -> None:
    source_root = tmp_path / "work"
    source_root.mkdir()
    source = source_root / "dostoevsky"
    text = "An available work is present, but another referenced text version is missing.\n"
    _named_prepared_source(
        source,
        work_id="dostoevsky-work",
        version_id="dostoevsky-v1",
        author="Available Author",
        title="Available Work",
        text=text,
    )
    questions = tmp_path / "questions.json"
    _questions(questions)
    curation_root = tmp_path / "curated"
    curation_root.mkdir()
    (curation_root / "partial.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "passages": [
                    {"work_id": "dostoevsky-work", "text_version_id": "dostoevsky-v1"},
                    {"work_id": "missing-work", "text_version_id": "missing-v1"},
                ],
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.toml"
    _config(config_path)

    with pytest.raises(ValueError, match="only partially available"):
        build_available_corpus(
            load_config(config_path),
            source_root,
            tmp_path / "output",
            questions_path=questions,
            curation_root=curation_root,
        )
