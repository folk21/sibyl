"""Source-neutral text primitives that do not interpret literary meaning."""

import re

_WORD = re.compile(r"\S+")


def normalize_newlines(text: str) -> str:
    """Normalizes transport newline conventions without otherwise rewriting text."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def trim_blank_edge_lines(text: str) -> str:
    """Removes blank edge lines while preserving all non-edge text verbatim."""
    lines = text.splitlines(keepends=True)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "".join(lines)


def word_count(text: str) -> int:
    """Counts whitespace-delimited tokens for deterministic passage metadata/limits."""
    return len(_WORD.findall(text))
