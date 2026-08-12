import json
from pathlib import Path
import tomllib

from sibyl_corpus_builder.fetchers import FetchedSourceCandidate
from sibyl_corpus_builder.preparation import (
    _selection_registry_models,
    acquire_selection,
    prepare_selection_sources,
)
from sibyl_corpus_builder.registration import register_selection
from sibyl_corpus_builder.selection import SelectionManifest, SelectionWork, write_selection
from sibyl_corpus_builder.source_artifacts import write_source_artifact

_HTML = """
<html><body>
<div>Комментарии: 10</div>
<h1>Преступление и наказание</h1>
<h2>Часть первая</h2>
<p>В начале июля, в чрезвычайно жаркое время, под вечер, один молодой человек вышел из своей каморки.</p>
<p>Он был задавлен бедностью, но продолжал идти по улице и думать о своем намерении.</p>
</body></html>
""".encode()


def _selection(tmp_path: Path) -> tuple[Path, SelectionManifest]:
    manifest = SelectionManifest(
        source_family="libru",
        source_url="https://az.lib.ru/d/dostoewskij_f_m/",
        author="Федор Достоевский",
        language="ru",
        original_language="ru",
        category="literature",
        works=(
            SelectionWork(
                id="libru-dostoevsky-text-0060",
                registry_work_id="dostoevsky-crime-punishment-libru",
                title="Преступление и наказание",
                source_url="https://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml",
                decision="include",
                reason="developer review",
                year=1866,
                genres=("Проза", "Романы"),
            ),
            SelectionWork(
                id="libru-dostoevsky-letters",
                title="Письма",
                source_url="https://az.lib.ru/d/dostoewskij_f_m/text_pisma.shtml",
                decision="exclude",
                reason="epistolary",
            ),
        ),
    )
    path = tmp_path / "selection.toml"
    write_selection(manifest, path)
    return path, manifest


def test_prepare_selection_and_register_candidate_records(tmp_path: Path):
    selection_path, manifest = _selection(tmp_path)
    cache = tmp_path / "raw"
    selected = manifest.included()[0]
    work, version = _selection_registry_models(manifest, selected)
    artifact = write_source_artifact(
        cache_dir=cache,
        work=work,
        version=version,
        raw=_HTML,
        resolved_uri="https://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml",
        artifact_kind="html",
    )

    prepared = tmp_path / "prepared"
    prepare_selection_sources(
        selection_path=selection_path,
        cache_dir=cache,
        output_dir=prepared,
    )
    prepared_manifest = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
    entry = prepared_manifest["works"][0]
    assert entry["id"] == "dostoevsky-crime-punishment-libru"
    assert entry["text_version_id"] == "dostoevsky-crime-punishment-libru-libru"
    assert entry["source_artifact_sha256"] == artifact.raw_sha256
    assert "normalizer=libru_html_v1" in entry["source_locator"]

    registry = tmp_path / "registry"
    written = register_selection(
        selection_path=selection_path,
        cache_dir=cache,
        registry_dir=registry,
        collection_id="dostoevsky-libru",
    )
    assert len(written) == 2
    work_record = tomllib.loads(
        (registry / "works" / "dostoevsky-crime-punishment-libru.toml").read_text(
            encoding="utf-8"
        )
    )
    version_record = work_record["text_versions"][0]
    assert work_record["enabled"] is False
    assert work_record["review_status"] == "candidate"
    assert version_record["id"] == "dostoevsky-crime-punishment-libru-libru"
    assert version_record["rights_status"] == "review_required"
    assert version_record["download_uri"].endswith("text_0060.shtml")
    assert "libru_html_v1" in version_record["provenance"]
    assert version_record["artifact_sha256"] == artifact.raw_sha256

    collection = tomllib.loads(
        (registry / "collections" / "dostoevsky-libru.toml").read_text(encoding="utf-8")
    )
    assert collection["works"] == ["dostoevsky-crime-punishment-libru"]


def test_acquire_selection_falls_back_and_isolates_failed_works(tmp_path: Path, monkeypatch):
    manifest = SelectionManifest(
        source_family="libru",
        source_url="https://az.lib.ru/d/dostoewskij_f_m/",
        author="Федор Достоевский",
        language="ru",
        original_language="ru",
        category="literature",
        works=(
            SelectionWork(
                id="good-work",
                title="Преступление и наказание",
                source_url="https://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml",
                decision="include",
                reason="reviewed",
            ),
            SelectionWork(
                id="bad-work",
                title="Неисправный текст",
                source_url="https://az.lib.ru/d/dostoewskij_f_m/text_bad.shtml",
                decision="include",
                reason="reviewed",
            ),
            SelectionWork(
                id="letters",
                title="Письма",
                source_url="https://az.lib.ru/d/dostoewskij_f_m/text_letters.shtml",
                decision="exclude",
                reason="epistolary",
            ),
        ),
    )
    selection_path = tmp_path / "selection.toml"
    write_selection(manifest, selection_path)

    invalid_fb2 = b"<FictionBook><body><p>broken</body></FictionBook>"

    def fake_candidates(version):
        if version.source_uri.endswith("text_0060.shtml"):
            return (
                FetchedSourceCandidate(
                    "fb2",
                    invalid_fb2,
                    "https://az.lib.ru/d/dostoewskij_f_m/text_0060.fb2",
                ),
                FetchedSourceCandidate("html", _HTML, version.source_uri),
            )
        return (
            FetchedSourceCandidate(
                "fb2",
                invalid_fb2,
                "https://az.lib.ru/d/dostoewskij_f_m/text_bad.fb2",
            ),
        )

    monkeypatch.setattr(
        "sibyl_corpus_builder.preparation.iter_text_version_candidates", fake_candidates
    )
    report_path = tmp_path / "acquire-report.toml"
    report = acquire_selection(
        selection_path=selection_path,
        cache_dir=tmp_path / "raw",
        report_path=report_path,
    )

    assert len(report.acquired) == 1
    assert report.acquired[0].work_id == "good-work"
    assert report.acquired[0].artifact_kind == "html"
    assert report.acquired[0].normalizer == "libru_html_v1"
    assert len(report.failed) == 1
    assert report.failed[0].work_id == "bad-work"
    assert "Invalid FB2 XML document" in (report.failed[0].error or "")
    assert len(report.skipped) == 1
    assert report.skipped[0].work_id == "letters"

    report_data = tomllib.loads(report_path.read_text(encoding="utf-8"))
    assert report_data["acquired_count"] == 1
    assert report_data["failed_count"] == 1
    assert report_data["skipped_count"] == 1
    assert {item["status"] for item in report_data["items"]} == {
        "acquired",
        "failed",
        "skipped",
    }
