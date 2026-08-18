import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from sibyl_corpus_builder.cli import build_parser
from sibyl_corpus_builder.curation import (
    export_curation_bundle,
    import_curation,
    load_question_catalog,
    validate_curated_curation,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _questions(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_id": "fixture-questions-v1",
                "language": "en",
                "items": [
                    {
                        "id": "change_timing",
                        "kind": "question",
                        "theme": "change",
                        "text": "When is it time to change?",
                    },
                    {
                        "id": "uncertainty",
                        "kind": "state",
                        "theme": "change",
                        "text": "I do not know what comes next.",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _prepared_source(path: Path) -> str:
    path.mkdir()
    text = (
        "The first paragraph asks whether a familiar life should continue.\n\n"
        "The second paragraph accepts uncertainty and chooses a different road.\n"
    )
    digest = _sha256(text)
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
                        "canonical_text_sha256": digest,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return text


def _add_prepared_work(path: Path, *, work_id: str, rights_status: str) -> str:
    text = f"Canonical text for {work_id}.\n"
    version_id = f"{work_id}-v1"
    file_name = f"{version_id}.txt"
    (path / file_name).write_text(text, encoding="utf-8")
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["works"].append(
        {
            "id": work_id,
            "text_version_id": version_id,
            "author": "Fixture Author",
            "title": f"Fixture {work_id}",
            "file": file_name,
            "source_name": "Fixture Source",
            "language": "en",
            "original_language": "en",
            "category": "literature",
            "text_role": "original",
            "rights_status": rights_status,
            "canonical_text_sha256": _sha256(text),
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return text


def _proposal(path: Path, text: str, *, text_hash: str | None = None) -> tuple[int, int]:
    selected = "The second paragraph accepts uncertainty and chooses a different road."
    start = text.index(selected)
    end = start + len(selected)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "proposal_id": "fixture-author-v1",
                "question_catalog_id": "fixture-questions-v1",
                "curation_method": "large_llm",
                "source_bundle_id": "cb_0123456789abcdefabcd",
                "passages": [
                    {
                        "work_id": "fixture-work",
                        "text_version_id": "fixture-v1",
                        "canonical_sha256": _sha256(text),
                        "source_locator": f"chars:{start}:{end}",
                        "text_sha256": text_hash or _sha256(selected),
                        "matches": [
                            {"question_id": "uncertainty", "strength": 0.94},
                            {"question_id": "change_timing", "strength": 0.82},
                        ],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return start, end


def test_project_guided_question_catalog_has_66_stable_unique_items() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    catalog = load_question_catalog(repository_root / "corpus-curation" / "questions.json")

    assert catalog.catalog_id == "sibyl-guided-questions-ru-v1"
    assert catalog.language == "ru"
    assert len(catalog.items) == 66
    assert len(catalog.ids) == 66
    assert {item.kind for item in catalog.items} == {"question", "state"}


def test_export_curation_bundle_contains_exact_canonical_text_and_is_reproducible(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    canonical = _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)

    first = export_curation_bundle(
        source_dir=source,
        questions_path=questions,
        output_path=tmp_path / "first.zip",
    )
    second = export_curation_bundle(
        source_dir=source,
        questions_path=questions,
        output_path=tmp_path / "second.zip",
    )

    assert first.read_bytes() == second.read_bytes()
    with ZipFile(first) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["purpose"] == "llm_passage_curation"
        assert manifest["question_catalog"]["catalog_id"] == "fixture-questions-v1"
        work = manifest["works"][0]
        assert work["work_id"] == "fixture-work"
        assert work["canonical_sha256"] == _sha256(canonical)
        assert archive.read(work["file"]).decode("utf-8") == canonical


def test_export_curation_bundle_requires_explicit_override_for_unapproved_rights(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _prepared_source(source)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["works"][0]["rights_status"] = "review_required"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    questions = tmp_path / "questions.json"
    _questions(questions)

    with pytest.raises(ValueError, match="without approved rights metadata"):
        export_curation_bundle(
            source_dir=source,
            questions_path=questions,
            output_path=tmp_path / "blocked.zip",
        )

    export_curation_bundle(
        source_dir=source,
        questions_path=questions,
        output_path=tmp_path / "allowed.zip",
        allow_unapproved=True,
    )


def test_export_curation_bundle_approved_only_skips_unapproved_sources(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    approved_text = _prepared_source(source)
    _add_prepared_work(source, work_id="review-work", rights_status="review_required")
    questions = tmp_path / "questions.json"
    _questions(questions)

    output = export_curation_bundle(
        source_dir=source,
        questions_path=questions,
        output_path=tmp_path / "approved.zip",
        approved_only=True,
    )

    with ZipFile(output) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert [work["work_id"] for work in manifest["works"]] == ["fixture-work"]
        work = manifest["works"][0]
        assert archive.read(work["file"]).decode("utf-8") == approved_text


def test_export_curation_bundle_approved_only_rejects_empty_result(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _prepared_source(source)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["works"][0]["rights_status"] = "review_required"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    questions = tmp_path / "questions.json"
    _questions(questions)

    with pytest.raises(ValueError, match="no approved source versions"):
        export_curation_bundle(
            source_dir=source,
            questions_path=questions,
            output_path=tmp_path / "approved.zip",
            approved_only=True,
        )


def test_export_curation_bundle_rejects_conflicting_rights_modes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)

    with pytest.raises(ValueError, match="mutually exclusive"):
        export_curation_bundle(
            source_dir=source,
            questions_path=questions,
            output_path=tmp_path / "invalid.zip",
            approved_only=True,
            allow_unapproved=True,
        )


def test_export_curation_cli_rights_modes_are_mutually_exclusive() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "export-curation-bundle",
                "--source",
                "source",
                "--questions",
                "questions.json",
                "--output",
                "bundle.zip",
                "--approved-only",
                "--allow-unapproved",
            ]
        )


def test_import_curation_verifies_exact_slice_and_writes_git_safe_metadata(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    canonical = _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)
    proposal = tmp_path / "proposal.json"
    start, end = _proposal(proposal, canonical)

    output = import_curation(
        source_dir=source,
        questions_path=questions,
        input_path=proposal,
        output_path=tmp_path / "curated.json",
    )
    data = json.loads(output.read_text(encoding="utf-8"))
    passage = data["passages"][0]

    assert passage["passage_id"].startswith("cp_")
    assert passage["source_locator"] == f"chars:{start}:{end}"
    assert passage["word_count"] > 0
    assert [match["question_id"] for match in passage["matches"]] == [
        "change_timing",
        "uncertainty",
    ]
    assert "text" not in passage
    assert "second paragraph" not in output.read_text(encoding="utf-8")

    validate_curated_curation(
        source_dir=source,
        questions_path=questions,
        curation_path=output,
    )


def test_import_curation_rejects_text_hash_that_does_not_match_canonical_slice(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    canonical = _prepared_source(source)
    questions = tmp_path / "questions.json"
    _questions(questions)
    proposal = tmp_path / "proposal.json"
    _proposal(proposal, canonical, text_hash="0" * 64)

    with pytest.raises(ValueError, match="text SHA-256 mismatch"):
        import_curation(
            source_dir=source,
            questions_path=questions,
            input_path=proposal,
            output_path=tmp_path / "curated.json",
        )
