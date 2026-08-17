from sibyl_corpus_builder.sources._internal.adapters import canonicalize_source


def test_gutenberg_wrapper_is_removed_without_rewriting_literary_text() -> None:
    raw = (
        "Project Gutenberg metadata\r\n"
        "*** START OF THE PROJECT GUTENBERG EBOOK FIXTURE ***\r\n"
        "\r\n"
        "First line.\r\n\r\nSecond  line with  spacing.\r\n"
        "\r\n"
        "*** END OF THE PROJECT GUTENBERG EBOOK FIXTURE ***\r\n"
        "Footer\r\n"
    ).encode()

    text, normalizer = canonicalize_source(raw, "project_gutenberg")

    assert normalizer == "project_gutenberg_v1"
    assert text == "First line.\n\nSecond  line with  spacing.\n"
