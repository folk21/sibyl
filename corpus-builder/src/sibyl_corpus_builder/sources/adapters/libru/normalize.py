"""Lib.ru canonical-text normalization.

Pipeline position:

    acquired Lib.ru TXT/HTML/FB2 bytes -> THIS MODULE -> canonical literary text
                                                   -> cached SourceArtifact

Lib.ru pages contain site chrome, comments, ratings, download links, and footer navigation.
This adapter removes only recognized transport/site wrappers. It does not paraphrase or rewrite
literary wording. TXT is preferred, HTML is a resilient fallback, and FB2 delegates to the
generic FB2 format adapter. Any semantic change to canonical output requires a new normalizer
version because downstream passage locators and hashes depend on exact character positions.
"""

import re
from html.parser import HTMLParser

from sibyl_corpus_core.text import normalize_newlines, trim_blank_edge_lines

from ..formats.fb2 import canonicalize_fb2
from .discovery import decode_html

_HTML_MARKER = re.compile(br"^\s*(?:<!doctype\s+html\b|<html\b)", re.I)
_XML_MARKER = re.compile(br"^\s*(?:<\?xml\b[^>]*>\s*)?<[^>]*fictionbook\b", re.I)
_WHITESPACE = re.compile(r"\s+")


def _decode_text(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    for encoding in ("utf-8", "cp1251", "koi8-r"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError("Lib.ru text could not be decoded as UTF-8, CP1251, or KOI8-R")


class _HtmlTextParser(HTMLParser):
    """Extracts readable Lib.ru body blocks while ignoring non-literary control content.

    Lib.ru may wrap the entire readable document in a ``form`` element, so forms are
    structural containers here rather than an automatic skip boundary.
    """

    _HARD_SKIP = {"head", "script", "style", "noscript"}
    _SELECT_CONTENT = {"option", "optgroup"}
    _BLOCKS = {
        "address", "article", "blockquote", "br", "div", "h1", "h2", "h3", "h4", "h5",
        "h6", "hr", "li", "p", "pre", "section", "table", "td", "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._parts: list[str] = []
        self._hard_skip_depth = 0
        self._select_depth = 0
        self._pre_depth = 0

    def _flush(self) -> None:
        if not self._parts:
            return
        raw = "".join(self._parts)
        if self._pre_depth:
            text = trim_blank_edge_lines(normalize_newlines(raw)).strip("\n")
        else:
            text = _WHITESPACE.sub(" ", raw).strip()
        if text:
            self.blocks.append(text)
        self._parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.casefold()
        if lower in self._HARD_SKIP:
            self._hard_skip_depth += 1
            return
        if self._hard_skip_depth:
            return

        if lower == "select":
            self._select_depth += 1
            return
        if self._select_depth:
            if lower in self._SELECT_CONTENT:
                return
            # Old Lib.ru markup can leave a navigation <select> unclosed. Browsers
            # implicitly close it when incompatible content such as <input>, headings,
            # or the literary <pre> starts; HTMLParser does not perform that recovery.
            self._select_depth = 0

        if lower in self._BLOCKS:
            self._flush()
        if lower == "pre":
            self._pre_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lower = tag.casefold()
        if lower in self._HARD_SKIP:
            if self._hard_skip_depth:
                self._hard_skip_depth -= 1
            return
        if self._hard_skip_depth:
            return

        if lower == "select":
            if self._select_depth:
                self._select_depth -= 1
            return
        if lower in self._SELECT_CONTENT and self._select_depth:
            return
        if self._select_depth:
            return

        if lower in self._BLOCKS:
            self._flush()
        if lower == "pre" and self._pre_depth:
            self._pre_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hard_skip_depth and not self._select_depth:
            self._parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def _title_start(blocks: list[str], work_title: str | None) -> int:
    """Finds the reviewed title near the start while avoiding repeated footer/navigation text."""
    if not work_title:
        raise ValueError("Lib.ru HTML/TXT normalization requires the reviewed work title")
    wanted = " ".join(work_title.split()).casefold()
    total_chars = sum(len(block) for block in blocks)
    remaining = total_chars
    candidates: list[int] = []
    for index, block in enumerate(blocks):
        normalized = " ".join(block.split()).casefold()
        if wanted == normalized or (wanted in normalized and len(normalized) <= len(wanted) + 80):
            if remaining >= max(40, total_chars // 3):
                candidates.append(index)
        remaining -= len(block)
    if not candidates:
        raise ValueError(f"Could not locate Lib.ru literary body boundary for title: {work_title}")
    return candidates[-1]


def _trim_footer(blocks: list[str]) -> list[str]:
    """Stops at recognized Lib.ru footer markers only in the final third of the page."""
    if len(blocks) < 4:
        return blocks
    footer_markers = (
        "lib.ru/классика",
        "вернуться на страницу автора",
        "добавить комментарий",
        "copyright ©",
    )
    threshold = max(1, len(blocks) * 2 // 3)
    for index in range(threshold, len(blocks)):
        normalized = blocks[index].casefold().strip()
        if any(normalized.startswith(marker) for marker in footer_markers):
            return blocks[:index]
    return blocks


def canonicalize_html(raw: bytes, work_title: str | None) -> str:
    """Extracts the literary body from a Lib.ru work page and removes recognized site chrome."""
    parser = _HtmlTextParser()
    parser.feed(decode_html(raw))
    parser.close()
    if not parser.blocks:
        raise ValueError("Lib.ru HTML contains no readable text blocks")
    start = _title_start(parser.blocks, work_title)
    blocks = _trim_footer(parser.blocks[start:])
    text = "\n\n".join(blocks).strip()
    if len(text) < 40:
        raise ValueError("Lib.ru HTML literary body is implausibly short")
    return text


def canonicalize_txt(raw: bytes, work_title: str | None) -> str:
    """Normalizes Lib.ru text encoding/newlines and removes a recognized site wrapper if present."""
    text = normalize_newlines(_decode_text(raw))
    stripped = trim_blank_edge_lines(text)
    if not work_title:
        return stripped

    blocks = [block.strip() for block in re.split(r"\n\s*\n+", stripped) if block.strip()]
    if len(blocks) <= 1:
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Lib.ru TXT is empty")
        start = _title_start(lines, work_title)
        return "\n".join(lines[start:])

    try:
        start = _title_start(blocks, work_title)
    except ValueError:
        # Some internal Lib.ru TXT endpoints already start directly with literary content.
        return stripped
    return "\n\n".join(blocks[start:])


def _detect_kind(raw: bytes) -> str:
    if raw.startswith(b"PK"):
        return "fb2"
    prefix = raw[:8192]
    if _XML_MARKER.search(prefix):
        return "fb2"
    if _HTML_MARKER.search(prefix) or b"<body" in prefix.lower():
        return "html"
    return "txt"


def canonicalize(
    raw: bytes,
    *,
    work_title: str | None,
    artifact_kind: str | None,
) -> tuple[str, str]:
    """Routes one Lib.ru artifact to the versioned TXT/HTML/FB2 canonicalizer."""
    detected_kind = _detect_kind(raw)
    kind = detected_kind if detected_kind != "txt" else (artifact_kind or detected_kind)
    if kind == "txt":
        return canonicalize_txt(raw, work_title), "libru_txt_v1"
    if kind == "html":
        return canonicalize_html(raw, work_title), "libru_html_v1"
    if kind == "fb2":
        return canonicalize_fb2(raw), "libru_fb2_v1"
    raise ValueError(f"Unsupported Lib.ru artifact kind: {kind!r}")
