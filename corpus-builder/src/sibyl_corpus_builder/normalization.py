import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from io import BytesIO
from zipfile import BadZipFile, ZipFile

_START_MARKER = re.compile(r"^\*{3}\s*START OF (?:THIS |THE )?PROJECT GUTENBERG EBOOK\b", re.I)
_END_MARKER = re.compile(r"^\*{3}\s*END OF (?:THIS |THE )?PROJECT GUTENBERG EBOOK\b", re.I)
_HTML_MARKER = re.compile(br"^\s*(?:<!doctype\s+html\b|<html\b)", re.I)
_XML_MARKER = re.compile(br"^\s*(?:<\?xml\b[^>]*>\s*)?<[^>]*fictionbook\b", re.I)
_WHITESPACE = re.compile(r"\s+")


def decode_text(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Source artifact is not valid UTF-8; convert it explicitly before import"
        ) from error


def _decode_libru_text(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    for encoding in ("utf-8", "cp1251", "koi8-r"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError("Lib.ru text could not be decoded as UTF-8, CP1251, or KOI8-R")


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _trim_blank_edge_lines(text: str) -> str:
    lines = text.splitlines(keepends=True)
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "".join(lines)


def strip_project_gutenberg_wrapper(text: str) -> str:
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

    return _trim_blank_edge_lines("".join(lines[start_index:end_index]))


def _fb2_payload(raw: bytes) -> bytes:
    if not raw.startswith(b"PK"):
        return raw
    try:
        with ZipFile(BytesIO(raw)) as archive:
            candidates = sorted(
                name
                for name in archive.namelist()
                if name.lower().endswith((".fb2", ".xml")) and not name.endswith("/")
            )
            if not candidates:
                raise ValueError("FB2 ZIP archive contains no .fb2 or .xml document")
            return archive.read(candidates[0])
    except BadZipFile as error:
        raise ValueError("Invalid FB2 ZIP archive") from error


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _inline_text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def canonicalize_fb2(raw: bytes) -> str:
    payload = _fb2_payload(raw)
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError("Invalid FB2 XML document") from error

    bodies = [element for element in root.iter() if _local_name(element.tag) == "body"]
    primary = next(
        (
            body
            for body in bodies
            if body.attrib.get("name", "").casefold() not in {"notes", "comments"}
        ),
        None,
    )
    if primary is None:
        raise ValueError("FB2 document contains no primary body")

    blocks: list[str] = []
    for element in primary.iter():
        name = _local_name(element.tag)
        if name not in {"p", "subtitle", "v", "text-author"}:
            continue
        text = _inline_text(element)
        if text:
            blocks.append(text)
    if not blocks:
        raise ValueError("FB2 primary body contains no text blocks")
    return "\n\n".join(blocks)


class _LibRuHtmlTextParser(HTMLParser):
    _SKIP = {"head", "script", "style", "form", "select", "option", "noscript"}
    _BLOCKS = {
        "address",
        "article",
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._parts: list[str] = []
        self._skip_depth = 0
        self._pre_depth = 0

    def _flush(self) -> None:
        if not self._parts:
            return
        raw = "".join(self._parts)
        if self._pre_depth:
            text = _trim_blank_edge_lines(normalize_newlines(raw)).strip("\n")
        else:
            text = _WHITESPACE.sub(" ", raw).strip()
        if text:
            self.blocks.append(text)
        self._parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.casefold()
        if lower in self._SKIP:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if lower in self._BLOCKS:
            self._flush()
        if lower == "pre":
            self._pre_depth += 1

    def handle_endtag(self, tag: str) -> None:
        lower = tag.casefold()
        if lower in self._SKIP:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if lower in self._BLOCKS:
            self._flush()
        if lower == "pre" and self._pre_depth:
            self._pre_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def _title_start(blocks: list[str], work_title: str | None) -> int:
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


def _trim_libru_footer(blocks: list[str]) -> list[str]:
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


def canonicalize_libru_html(raw: bytes, work_title: str | None) -> str:
    from .libru import decode_libru_html

    parser = _LibRuHtmlTextParser()
    parser.feed(decode_libru_html(raw))
    parser.close()
    if not parser.blocks:
        raise ValueError("Lib.ru HTML contains no readable text blocks")
    start = _title_start(parser.blocks, work_title)
    blocks = _trim_libru_footer(parser.blocks[start:])
    text = "\n\n".join(blocks).strip()
    if len(text) < 40:
        raise ValueError("Lib.ru HTML literary body is implausibly short")
    return text


def canonicalize_libru_txt(raw: bytes, work_title: str | None) -> str:
    text = normalize_newlines(_decode_libru_text(raw))
    stripped = _trim_blank_edge_lines(text)
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
        # A raw internal Lib.ru TXT may already start directly with the literary content.
        return stripped
    return "\n\n".join(blocks[start:])


def _detect_libru_kind(raw: bytes) -> str:
    if raw.startswith(b"PK"):
        return "fb2"
    prefix = raw[:8192]
    if _XML_MARKER.search(prefix):
        return "fb2"
    if _HTML_MARKER.search(prefix) or b"<body" in prefix.casefold():
        return "html"
    return "txt"


def canonicalize_text(
    raw: bytes,
    source_family: str,
    *,
    work_title: str | None = None,
    artifact_kind: str | None = None,
) -> tuple[str, str]:
    if source_family == "libru":
        detected_kind = _detect_libru_kind(raw)
        kind = detected_kind if detected_kind != "txt" else (artifact_kind or detected_kind)
        if kind == "txt":
            return canonicalize_libru_txt(raw, work_title), "libru_txt_v1"
        if kind == "html":
            return canonicalize_libru_html(raw, work_title), "libru_html_v1"
        if kind == "fb2":
            return canonicalize_fb2(raw), "libru_fb2_v1"
        raise ValueError(f"Unsupported Lib.ru artifact kind: {kind!r}")

    text = normalize_newlines(decode_text(raw))
    if source_family == "project_gutenberg":
        return strip_project_gutenberg_wrapper(text), "project_gutenberg_v1"
    return _trim_blank_edge_lines(text), "plain_text_v1"
