from sibyl_corpus_builder.config import PassageConfig
from sibyl_corpus_builder.models import SourceDocument
from sibyl_corpus_builder.splitter import split_document


def test_splitter_respects_paragraph_boundaries_and_maximum() -> None:
    document = SourceDocument(
        source_id="work",
        text_version_id="work:source",
        author="Fixture",
        work="Fixture work",
        source_name="fixture.txt",
        language="en",
        original_language="en",
        category="literature",
        text_role="original",
        text=(
            "one two three four five six seven eight nine ten\n\n"
            "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen\n\n"
            "nineteen twenty twenty-one twenty-two twenty-three twenty-four"
        ),
    )
    config = PassageConfig(min_words=5, preferred_words=10, max_words=20, overlap_paragraphs=0)

    passages = split_document(document, config)

    assert passages
    assert all(passage.word_count <= 20 for passage in passages)
    assert all("\n\n" in passage.text or passage.word_count >= 5 for passage in passages)


def test_splitter_uses_exact_source_slices_and_splits_long_paragraphs() -> None:
    text = (
        "One sentence has several useful words for this fixture. "
        "Another sentence has several more useful words for this fixture. "
        "A final sentence keeps the paragraph intentionally longer than the configured limit."
    )
    document = SourceDocument(
        source_id="long-work",
        text_version_id="long-work:source",
        author="Fixture",
        work="Long fixture",
        source_name="fixture.txt",
        language="en",
        original_language="en",
        category="literature",
        text_role="original",
        text=text,
    )
    config = PassageConfig(min_words=4, preferred_words=8, max_words=12, overlap_paragraphs=0)

    passages = split_document(document, config)

    assert len(passages) >= 2
    for passage in passages:
        assert passage.word_count <= 12
        assert document.text[passage.source_start : passage.source_end] == passage.text
        assert passage.source_locator == f"chars:{passage.source_start}:{passage.source_end}"
