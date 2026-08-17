"""Project Gutenberg canonical-text normalization.

The adapter runs after a plain-text artifact has been acquired. It removes only the standard
Project Gutenberg transport wrapper between START/END markers and preserves literary wording,
spacing, and paragraph structure inside that boundary.
"""

import re

from sibyl_corpus_core.text import normalize_newlines, trim_blank_edge_lines

_START_MARKER = re.compile(r"^\*{3}\s*START OF (?:THIS |THE )?PROJECT GUTENBERG EBOOK\b", re.I)
_END_MARKER = re.compile(r"^\*{3}\s*END OF (?:THIS |THE )?PROJECT GUTENBERG EBOOK\b", re.I)


def canonicalize(text: str) -> str:
    """Removes Gutenberg wrapper lines while leaving the enclosed literary text unchanged."""
    text = normalize_newlines(text)
    lines = text.splitlines(keepends=True)
    start_index: int | None = None
    end_index: int | None = None

    for index, line in enumerate(lines):
        if _START_MARKER.match(line.strip()):
            start_index = index + 1
            break
    if start_index is None:
        raise ValueError("Project Gutenberg START marker was not found")

    for index in range(start_index, len(lines)):
        if _END_MARKER.match(lines[index].strip()):
            end_index = index
            break
    if end_index is None:
        raise ValueError("Project Gutenberg END marker was not found")

    return trim_blank_edge_lines("".join(lines[start_index:end_index]))
