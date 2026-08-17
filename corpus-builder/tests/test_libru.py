from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from sibyl_corpus_builder.sources.adapters.libru.discovery import (
    discover_author_page as discover_libru_author_page,
)
from sibyl_corpus_builder.sources.adapters.libru.fetch import (
    discover_artifact_candidates as discover_libru_artifact_candidates,
    discover_fb2_uri,
)
from sibyl_corpus_builder.sources._internal.adapters import canonicalize_source
from sibyl_corpus_builder.sources.api import load_selection, write_selection


_AUTHOR_PAGE = """
<html>
<head><title>Lib.ru/Классика: Достоевский Федор Михайлович. Полное собрание сочинений</title></head>
<body>
<a href="text_0010.shtml">Бедные люди</a> [1846] <a href="/PROZA/">Проза</a> Романы
<a href="text_0060.shtml">Преступление и наказание</a> [1866] <a href="/PROZA/">Проза</a> Романы
<a href="text_1868_pisma.shtml">Письма 1860-1868</a> [1868] Эпистолярий Переписка и речи
<a href="text_1872_besy_ruk_redaktzii.shtml">Бесы. Рукописные редакции</a>
[1872] Проза Рукописные редакции
<a href="/p/pisarew_d/text_1867.shtml">Погибшие и погибающие</a> [1867] Критика О Достоевском
</body>
</html>
""".encode()

_WORK_PAGE = """
<html><head><title>Lib.ru/Классика: Достоевский. Преступление и наказание</title></head>
<body>
<div>Комментарии: 312</div>
<a href="text_0060.txt">txt (Word,КПК)</a>
<a href="/d/dostoewskij_f_m/text_0060.fb2.zip">Скачать FB2</a>
<form><span>Ваша оценка</span></form>
<div>Аннотация: Роман в шести частях с эпилогом.</div>
<h1>Преступление и наказание</h1>
<h2>Часть первая</h2>
<p>В начале июля, в чрезвычайно жаркое время, под вечер, один молодой человек вышел из своей каморки.</p>
<p>Он был задавлен бедностью; но даже стесненное положение перестало в последнее время тяготить его.</p>
<div>Вернуться на страницу автора</div>
</body></html>
""".encode()

_FB2 = '''<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <body>
    <section>
      <title><p>Часть первая</p></title>
      <p>Первый <emphasis>абзац</emphasis> текста.</p>
      <p>Второй абзац.</p>
    </section>
  </body>
  <body name="notes"><section><p>Редакторское примечание.</p></section></body>
</FictionBook>'''.encode()


def _zip_fb2() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("book.fb2", _FB2)
    return buffer.getvalue()


def test_discover_libru_author_page_classifies_literature_and_correspondence(tmp_path: Path):
    manifest = discover_libru_author_page(
        "https://az.lib.ru/d/dostoewskij_f_m", _AUTHOR_PAGE
    )

    assert manifest.author == "Достоевский Федор Михайлович"
    assert manifest.source_url == "https://az.lib.ru/d/dostoewskij_f_m/"
    assert manifest.works[0].source_url == "https://az.lib.ru/d/dostoewskij_f_m/text_0010.shtml"
    assert [work.title for work in manifest.works] == [
        "Бедные люди",
        "Преступление и наказание",
        "Письма 1860-1868",
        "Бесы. Рукописные редакции",
    ]
    decisions = {work.title: work.decision for work in manifest.works}
    assert decisions["Бедные люди"] == "include"
    assert decisions["Преступление и наказание"] == "include"
    assert decisions["Письма 1860-1868"] == "exclude"
    assert decisions["Бесы. Рукописные редакции"] == "review"

    path = tmp_path / "selection.toml"
    write_selection(manifest, path)
    loaded = load_selection(path)
    assert loaded == manifest


def test_libru_artifact_candidates_prefer_txt_then_html_then_fb2():
    candidates = discover_libru_artifact_candidates(
        "https://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml", _WORK_PAGE
    )

    assert [candidate.kind for candidate in candidates] == ["txt", "html", "fb2"]
    assert candidates[0].uri.endswith("text_0060.txt")
    assert candidates[1].uri.endswith("text_0060.shtml")
    assert candidates[2].uri.endswith("text_0060.fb2.zip")


def test_discover_fb2_uri_remains_available_for_diagnostics():
    assert discover_fb2_uri(
        "https://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml", _WORK_PAGE
    ) == "https://az.lib.ru/d/dostoewskij_f_m/text_0060.fb2.zip"


def test_libru_html_normalization_extracts_literary_body_and_removes_page_chrome():
    text, normalizer = canonicalize_source(
        _WORK_PAGE,
        "libru",
        work_title="Преступление и наказание",
        artifact_kind="html",
    )

    assert normalizer == "libru_html_v1"
    assert text.startswith("Преступление и наказание\n\nЧасть первая")
    assert "В начале июля" in text
    assert "Комментарии: 312" not in text
    assert "Скачать FB2" not in text
    assert "Ваша оценка" not in text
    assert "Вернуться на страницу автора" not in text


def test_libru_content_sniff_overrides_misleading_txt_candidate_kind():
    text, normalizer = canonicalize_source(
        _WORK_PAGE,
        "libru",
        work_title="Преступление и наказание",
        artifact_kind="txt",
    )

    assert normalizer == "libru_html_v1"
    assert "В начале июля" in text


def test_libru_fb2_normalization_uses_primary_body_and_preserves_text():
    text, normalizer = canonicalize_source(_zip_fb2(), "libru")

    assert normalizer == "libru_fb2_v1"
    assert text == (
        "Часть первая\n\n"
        "Первый абзац текста.\n\n"
        "Второй абзац."
    )
    assert "Редакторское примечание" not in text


def test_selection_rejects_invalid_decision(tmp_path: Path):
    path = tmp_path / "selection.toml"
    path.write_text(
        '''schema_version = 1
source_family = "libru"
source_url = "https://az.lib.ru/d/dostoewskij_f_m/"
author = "D"
language = "ru"
original_language = "ru"
category = "literature"
[[works]]
id = "x"
title = "X"
source_url = "https://az.lib.ru/d/dostoewskij_f_m/text_x.shtml"
decision = "maybe"
''',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid selection decision"):
        load_selection(path)
