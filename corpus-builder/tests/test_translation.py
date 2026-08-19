import hashlib
import json
import sqlite3
from pathlib import Path
from zipfile import ZipFile

import pytest

from sibyl_corpus_builder.build.api import build_corpus
from sibyl_corpus_builder.build.config import load_config
from sibyl_corpus_builder.curation import import_curation
from sibyl_corpus_builder.translation import (
    export_translation_bundle,
    import_translation,
    load_validated_translation,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    canonical = (
        "The first foreign paragraph asks what a person owes to memory.\n\n"
        "The second foreign paragraph chooses mercy despite uncertainty.\n"
    )
    (source / "fixture-en.txt").write_text(canonical, encoding="utf-8")
    (source / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "works": [
                    {
                        "id": "foreign-work",
                        "text_version_id": "foreign-en",
                        "author": "Foreign Author",
                        "title": "Foreign Work",
                        "file": "fixture-en.txt",
                        "source_name": "Fixture Source",
                        "language": "en",
                        "original_language": "en",
                        "category": "literature",
                        "text_role": "original",
                        "rights_status": "approved",
                        "canonical_text_sha256": _sha256(canonical),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    questions = tmp_path / "questions.json"
    questions.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "catalog_id": "fixture-ru-v1",
                "language": "ru",
                "items": [
                    {
                        "id": "mercy",
                        "kind": "question",
                        "theme": "relationships",
                        "text": "Что значит проявить милосердие?",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    selected = "The second foreign paragraph chooses mercy despite uncertainty."
    start = canonical.index(selected)
    proposal = tmp_path / "curation-proposal.json"
    proposal.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "proposal_id": "foreign-curation-v1",
                "question_catalog_id": "fixture-ru-v1",
                "curation_method": "large_llm",
                "source_bundle_id": "cb_0123456789abcdefabcd",
                "passages": [
                    {
                        "work_id": "foreign-work",
                        "text_version_id": "foreign-en",
                        "canonical_sha256": _sha256(canonical),
                        "source_locator": f"chars:{start}:{start + len(selected)}",
                        "text_sha256": _sha256(selected),
                        "matches": [{"question_id": "mercy", "strength": 0.9}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    curation = tmp_path / "curation.json"
    import_curation(
        source_dir=source,
        questions_path=questions,
        input_path=proposal,
        output_path=curation,
    )
    return source, questions, curation, selected


def _translation_proposal(bundle: Path, output: Path, source_text: str) -> None:
    with ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        passages = json.loads(archive.read("passages.json"))["passages"]
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "translation_id": "foreign-ru-v1",
                "source_bundle_id": manifest["bundle_id"],
                "source_curation_id": manifest["source_curation_id"],
                "translation_method": "large_llm",
                "target_language": "ru",
                "translation_provider": "fixture-provider",
                "translation_model": "fixture-model",
                "prompt_version": "literary-ru-v1",
                "passages": [
                    {
                        "passage_id": passages[0]["passage_id"],
                        "source_text_sha256": _sha256(source_text),
                        "text": (
                            "Второй иностранный абзац выбирает милосердие "
                            "вопреки неуверенности."
                        ),
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_translation_bundle_is_deterministic_and_contains_exact_curated_source(
    tmp_path: Path,
) -> None:
    source, questions, curation, selected = _fixture(tmp_path)
    first = export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "first.zip",
    )
    second = export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "second.zip",
    )

    assert first.read_bytes() == second.read_bytes()
    with ZipFile(first) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        payload = json.loads(archive.read("passages.json"))
    assert manifest["purpose"] == "curated_passage_machine_translation"
    assert payload["passages"][0]["text"] == selected
    assert payload["passages"][0]["source_text_sha256"] == _sha256(selected)


def test_translation_import_requires_complete_source_identity_and_persists_hashes(
    tmp_path: Path,
) -> None:
    source, questions, curation, selected = _fixture(tmp_path)
    bundle = export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "bundle.zip",
    )
    proposal = tmp_path / "translation-proposal.json"
    _translation_proposal(bundle, proposal, selected)
    output = import_translation(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        input_path=proposal,
        output_path=tmp_path / "validated.json",
    )
    validated = load_validated_translation(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        translation_path=output,
    )

    assert validated.target_language == "ru"
    assert validated.translation_provider == "fixture-provider"
    assert validated.passages[0].source_text_sha256 == _sha256(selected)
    assert validated.passages[0].text_sha256 == _sha256(validated.passages[0].text)


def test_translation_import_rejects_missing_required_passage(tmp_path: Path) -> None:
    source, questions, curation, _selected = _fixture(tmp_path)
    bundle = export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "bundle.zip",
    )
    with ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    proposal = tmp_path / "translation-proposal.json"
    proposal.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "translation_id": "foreign-ru-v1",
                "source_bundle_id": manifest["bundle_id"],
                "source_curation_id": manifest["source_curation_id"],
                "translation_method": "large_llm",
                "target_language": "ru",
                "translation_provider": "fixture-provider",
                "translation_model": "fixture-model",
                "prompt_version": "literary-ru-v1",
                "passages": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="contains no passages"):
        import_translation(
            source_dir=source,
            questions_path=questions,
            curation_path=curation,
            target_language="ru",
            input_path=proposal,
            output_path=tmp_path / "validated.json",
        )


def test_build_materializes_original_and_machine_translation_for_same_curated_passage(
    tmp_path: Path,
) -> None:
    source, questions, curation, selected = _fixture(tmp_path)
    bundle = export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "bundle.zip",
    )
    proposal = tmp_path / "translation-proposal.json"
    _translation_proposal(bundle, proposal, selected)
    translation = import_translation(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        input_path=proposal,
        output_path=tmp_path / "translation.json",
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[corpus]
format_version = 4
language = "ru"
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
    output = tmp_path / "output"
    build_corpus(
        load_config(config_path),
        source,
        output,
        questions_path=questions,
        curation_paths=[curation],
        translation_paths=[translation],
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["machine_translations"] == 1

    with sqlite3.connect(output / "corpus.db") as connection:
        passage_id = connection.execute(
            "SELECT passage_id FROM guided_question_passage WHERE question_id = 'mercy'"
        ).fetchone()[0]
        rows = connection.execute(
            """
            SELECT tv.language, tv.role, tv.translation_provider, pt.text
            FROM passage_text pt
            JOIN text_version tv ON tv.id = pt.text_version_id
            WHERE pt.passage_id = ?
            ORDER BY tv.role
            """,
            (passage_id,),
        ).fetchall()
    assert ("en", "original", None, selected) in rows
    assert any(
        language == "ru" and role == "machine_translation" and provider == "fixture-provider"
        for language, role, provider, _text in rows
    )


def test_available_translation_selection_skips_unavailable_and_rejects_partial(
    tmp_path: Path,
) -> None:
    from sibyl_corpus_builder.build._internal.available_inputs import select_available_translations

    unavailable = tmp_path / "unavailable.json"
    unavailable.write_text(
        json.dumps({"schema_version": 1, "passages": [{"passage_id": "other"}]}),
        encoding="utf-8",
    )
    selected, skipped = select_available_translations(
        available_passage_ids=frozenset({"present"}),
        translation_paths=(unavailable,),
    )
    assert selected == ()
    assert skipped == (unavailable,)

    partial = tmp_path / "partial.json"
    partial.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "passages": [{"passage_id": "present"}, {"passage_id": "missing"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="only partially available"):
        select_available_translations(
            available_passage_ids=frozenset({"present"}),
            translation_paths=(partial,),
        )


def test_translation_export_requires_explicit_override_for_unapproved_source(
    tmp_path: Path,
) -> None:
    source, questions, curation, _selected = _fixture(tmp_path)
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["works"][0]["rights_status"] = "review_required"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="without approved rights metadata"):
        export_translation_bundle(
            source_dir=source,
            questions_path=questions,
            curation_path=curation,
            target_language="ru",
            output_path=tmp_path / "blocked.zip",
        )

    export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "allowed.zip",
        allow_unapproved=True,
    )


def test_translation_commands_are_registered_on_root_cli() -> None:
    from sibyl_corpus_builder.cli import build_parser

    args = build_parser().parse_args(
        [
            "export-translation-bundle",
            "--source",
            "source",
            "--questions",
            "questions.json",
            "--curation",
            "curation.json",
            "--target-language",
            "ru",
            "--output",
            "bundle.zip",
        ]
    )
    assert args.command == "export-translation-bundle"
    assert args.target_language == "ru"


def test_build_available_discovers_compatible_validated_translation(tmp_path: Path) -> None:
    from sibyl_corpus_builder.build.api import build_available_corpus

    source, questions, curation, selected = _fixture(tmp_path)
    bundle = export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "bundle.zip",
    )
    proposal = tmp_path / "translation-proposal.json"
    _translation_proposal(bundle, proposal, selected)
    validated_translation = import_translation(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        input_path=proposal,
        output_path=tmp_path / "translation.json",
    )

    source_root = tmp_path / "work"
    source_root.mkdir()
    source.rename(source_root / "foreign")
    curation_root = tmp_path / "curated"
    curation_root.mkdir()
    curation.rename(curation_root / "foreign-v1.json")
    translation_root = tmp_path / "translations"
    translation_root.mkdir()
    validated_translation.rename(translation_root / "foreign-ru-v1.json")

    config_path = tmp_path / "available-config.toml"
    config_path.write_text(
        """
[corpus]
format_version = 4
language = "ru"
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
    output = tmp_path / "available-output"
    build_available_corpus(
        load_config(config_path),
        source_root,
        output,
        questions_path=questions,
        curation_root=curation_root,
        translation_root=translation_root,
    )

    with sqlite3.connect(output / "corpus.db") as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM text_version WHERE role = 'machine_translation'"
        ).fetchone()[0]
    assert count == 1


def test_translation_revalidation_fails_after_canonical_source_changes(tmp_path: Path) -> None:
    source, questions, curation, selected = _fixture(tmp_path)
    bundle = export_translation_bundle(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        output_path=tmp_path / "bundle.zip",
    )
    proposal = tmp_path / "translation-proposal.json"
    _translation_proposal(bundle, proposal, selected)
    translation = import_translation(
        source_dir=source,
        questions_path=questions,
        curation_path=curation,
        target_language="ru",
        input_path=proposal,
        output_path=tmp_path / "translation.json",
    )

    source_file = source / "fixture-en.txt"
    source_file.write_text(source_file.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="canonical SHA-256 mismatch"):
        load_validated_translation(
            source_dir=source,
            questions_path=questions,
            curation_path=curation,
            translation_path=translation,
        )
