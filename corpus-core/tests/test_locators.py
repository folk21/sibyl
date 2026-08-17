from sibyl_corpus_core.locators import CharacterRange, parse_character_locator


def test_character_locator_round_trip_and_exact_slice() -> None:
    text = "before exact literary text after"
    expected = "exact literary text"
    start = text.index(expected)
    character_range = CharacterRange(start, start + len(expected))

    assert parse_character_locator(character_range.locator) == character_range
    assert character_range.extract(text) == expected
