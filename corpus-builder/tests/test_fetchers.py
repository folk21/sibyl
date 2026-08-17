from sibyl_corpus_builder.sources.adapters.gutenberg.fetch import _GutenbergTextLinkParser


def test_gutenberg_parser_finds_current_plain_text_style_link() -> None:
    parser = _GutenbergTextLinkParser()
    parser.feed('<a href="/ebooks/15.txt.utf-8">Plain Text (accessible)</a>')

    assert parser.candidates == [("/ebooks/15.txt.utf-8", "Plain Text (accessible)")]


def test_libru_pinned_download_uri_is_not_re_discovered(monkeypatch) -> None:
    from sibyl_corpus_builder.sources.adapters.libru import fetch
    from sibyl_corpus_builder.sources._internal.registry import RegistryTextVersion

    calls: list[str] = []

    def fake_download(url: str, **_kwargs) -> bytes:
        calls.append(url)
        return b"pinned artifact"

    monkeypatch.setattr(fetch, "download", fake_download)
    version = RegistryTextVersion(
        id="dostoevsky-libru",
        language="ru",
        role="original",
        source_family="libru",
        source_name="Lib.ru / Классика",
        source_uri="https://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml",
        source_locator="pinned",
        rights_status="review_required",
        rights_jurisdiction="RU",
        provenance="test",
        download_uri="https://az.lib.ru/d/dostoewskij_f_m/text_0060.shtml",
    )

    candidates = tuple(fetch.iter_candidates(version))

    assert len(candidates) == 1
    assert candidates[0].kind == "auto"
    assert candidates[0].raw == b"pinned artifact"
    assert candidates[0].resolved_uri == version.download_uri
    assert calls == [version.download_uri]
