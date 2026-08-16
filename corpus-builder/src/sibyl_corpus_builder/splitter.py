import hashlib
import re
from dataclasses import dataclass

from .config import PassageConfig
from .models import PassageCandidate, SourceDocument

_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")
_SENTENCE_END = re.compile(r"[.!?…](?:[\"»”’')\]]+)?(?=\s|$)")
_WORD = re.compile(r"\S+")


@dataclass(frozen=True)
class _Unit:
    """A natural text unit with exact character offsets used while assembling passages."""

    start: int
    end: int
    word_count: int


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def _trim_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return None if start >= end else (start, end)


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _PARAGRAPH_BREAK.finditer(text):
        span = _trim_span(text, start, match.start())
        if span is not None:
            spans.append(span)
        start = match.end()
    span = _trim_span(text, start, len(text))
    if span is not None:
        spans.append(span)
    return spans


def _word_bounded_units(text: str, start: int, end: int, max_words: int) -> list[_Unit]:
    words = list(_WORD.finditer(text, start, end))
    units: list[_Unit] = []
    for offset in range(0, len(words), max_words):
        chunk = words[offset : offset + max_words]
        units.append(_Unit(start=chunk[0].start(), end=chunk[-1].end(), word_count=len(chunk)))
    return units


def _split_long_span(text: str, start: int, end: int, max_words: int) -> list[_Unit]:
    sentence_spans: list[tuple[int, int]] = []
    cursor = start
    for match in _SENTENCE_END.finditer(text, start, end):
        sentence = _trim_span(text, cursor, match.end())
        if sentence is not None:
            sentence_spans.append(sentence)
        cursor = match.end()
    tail = _trim_span(text, cursor, end)
    if tail is not None:
        sentence_spans.append(tail)

    if len(sentence_spans) <= 1:
        return _word_bounded_units(text, start, end, max_words)

    units: list[_Unit] = []
    group_start: int | None = None
    group_end: int | None = None
    group_words = 0
    for sentence_start, sentence_end in sentence_spans:
        sentence_words = word_count(text[sentence_start:sentence_end])
        if sentence_words > max_words:
            if group_start is not None and group_end is not None:
                units.append(_Unit(group_start, group_end, group_words))
                group_start = group_end = None
                group_words = 0
            units.extend(_word_bounded_units(text, sentence_start, sentence_end, max_words))
            continue
        if group_start is not None and group_words + sentence_words > max_words:
            assert group_end is not None
            units.append(_Unit(group_start, group_end, group_words))
            group_start = group_end = None
            group_words = 0
        if group_start is None:
            group_start = sentence_start
        group_end = sentence_end
        group_words += sentence_words
    if group_start is not None and group_end is not None:
        units.append(_Unit(group_start, group_end, group_words))
    return units


def _natural_units(text: str, max_words: int) -> list[_Unit]:
    units: list[_Unit] = []
    for start, end in _paragraph_spans(text):
        count = word_count(text[start:end])
        if count <= max_words:
            units.append(_Unit(start, end, count))
        else:
            units.extend(_split_long_span(text, start, end, max_words))
    return units


def split_document(document: SourceDocument, config: PassageConfig) -> list[PassageCandidate]:
    """Builds deterministic natural-boundary passages with exact canonical character locators."""
    units = _natural_units(document.text, config.max_words)
    results: list[PassageCandidate] = []
    index = 0
    ordinal = 0

    while index < len(units):
        selected: list[_Unit] = []
        count = 0
        cursor = index
        while cursor < len(units):
            unit = units[cursor]
            if selected and count + unit.word_count > config.max_words:
                break
            selected.append(unit)
            count += unit.word_count
            cursor += 1
            if count >= config.preferred_words:
                break

        if selected and count >= config.min_words:
            start = selected[0].start
            end = selected[-1].end
            text = document.text[start:end]
            actual_count = word_count(text)
            if actual_count > config.max_words:
                raise AssertionError("Passage splitter exceeded configured max_words")
            digest = hashlib.sha256(
                (
                    f"{document.source_id}:{document.text_version_id}:"
                    f"{start}:{end}:{text}"
                ).encode("utf-8")
            ).hexdigest()[:20]
            locator = f"chars:{start}:{end}"
            results.append(
                PassageCandidate(
                    passage_id=f"p_{digest}",
                    source_id=document.source_id,
                    text_version_id=document.text_version_id,
                    ordinal=ordinal,
                    text=text,
                    word_count=actual_count,
                    source_start=start,
                    source_end=end,
                    source_locator=locator,
                )
            )
            ordinal += 1

        if cursor <= index:
            cursor = index + 1
        overlap = min(config.overlap_paragraphs, max(0, len(selected) - 1))
        index = max(index + 1, cursor - overlap)

    return results
