"""Lib.ru author-catalog discovery.

Pipeline position:

    Lib.ru author URL -> THIS MODULE -> SelectionManifest -> editable selection.toml

Discovery classifies catalog entries conservatively for developer review. It never downloads
book bodies, approves rights, or writes permanent registry records. Correspondence is excluded,
clear literary categories are included, and ambiguous/non-fiction categories remain ``review``.
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from ...models import SelectionManifest, SelectionWork

_AUTHOR_TITLE_PATTERNS = (
    re.compile(r"Lib\.ru/Классика[:.]\s*(.+?)\.\s*Полное собрание", re.I),
    re.compile(r"Lib\.Ru\s*/\s*Классика:\s*(.+?)(?::|$)", re.I),
    re.compile(r"Lib\.Ru:\s*(.+?)$", re.I),
)
_YEAR = re.compile(r"\[([12]\d{3})\]")
_TEXT_PAGE = re.compile(r"^text_[^/?#]+\.shtml$", re.I)
_DIRECT_TEXT = re.compile(r"^[^/?#]+\.txt$", re.I)
_INCLUDE_MARKERS = (
    "проза", "роман", "повесть", "рассказ", "поэзия", "драматургия", "сказки", "детская",
)
_REVIEW_MARKERS = (
    "публицистика", "критика", "мемуары", "философия", "религия", "переводы", "рукопис",
    "наброс", "записн", "дневник", "dubia",
)
_EXCLUDE_MARKERS = ("эпистоляр", "переписк", "письма", "письмо ", "из писем", "на письмах")
_GENRE_NAMES = (
    "Проза", "Романы", "Поэзия", "Драматургия", "Сказки", "Детская", "Публицистика",
    "Критика", "Мемуары", "Философия", "Религия", "Переводы", "Эпистолярий",
)


@dataclass(frozen=True)
class _Anchor:
    """One parsed Lib.ru work link plus nearby catalog metadata used for classification."""

    href: str
    label: str
    context: str


class _DocumentParser(HTMLParser):
    """Collects page metadata and same-author work links from a Lib.ru catalog page."""

    def __init__(self) -> None:
        super().__init__()
        self.page_title_parts: list[str] = []
        self._in_title = False
        self._href: str | None = None
        self._anchor_text: list[str] = []
        self._nodes: list[tuple[str, str, str]] = []

    @property
    def page_title(self) -> str:
        return " ".join(" ".join(self.page_title_parts).split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower == "title":
            self._in_title = True
        if lower == "a":
            self._href = dict(attrs).get("href")
            self._anchor_text = []

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower == "title":
            self._in_title = False
        if lower == "a" and self._href is not None:
            label = " ".join(" ".join(self._anchor_text).split())
            self._nodes.append(("anchor", self._href, label))
            self._href = None
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.page_title_parts.append(data)
        if self._href is not None:
            self._anchor_text.append(data)
        elif data.strip():
            self._nodes.append(("text", "", data))

    def work_anchors(self, base_url: str) -> list[_Anchor]:
        """Returns work-page anchors and the catalog text between consecutive work links."""
        canonical_base = base_url.rstrip("/") + "/"
        parsed_base = urlparse(canonical_base)
        base_dir = parsed_base.path
        eligible_indexes: list[int] = []
        all_work_indexes: list[int] = []
        for index, (kind, href, _label) in enumerate(self._nodes):
            if kind != "anchor":
                continue
            absolute = urljoin(canonical_base, href)
            parsed = urlparse(absolute)
            file_name = parsed.path.rsplit("/", 1)[-1]
            if not (_TEXT_PAGE.fullmatch(file_name) or _DIRECT_TEXT.fullmatch(file_name)):
                continue
            all_work_indexes.append(index)
            if parsed.netloc == parsed_base.netloc and parsed.path.startswith(base_dir):
                eligible_indexes.append(index)

        anchors: list[_Anchor] = []
        for index in eligible_indexes:
            _kind, href, label = self._nodes[index]
            end = next(
                (candidate for candidate in all_work_indexes if candidate > index),
                len(self._nodes),
            )
            context_parts = [
                node_text
                for _node_kind, _node_href, node_text in self._nodes[index + 1 : end]
                if node_text
            ]
            anchors.append(
                _Anchor(
                    href=urljoin(canonical_base, href),
                    label=label,
                    context=" ".join(" ".join(context_parts).split()),
                )
            )
        return anchors


def decode_html(raw: bytes) -> str:
    """Decodes common Lib.ru encodings without silently replacing undecodable source bytes."""
    header = raw[:8192].decode("ascii", errors="ignore").casefold()
    for marker, encoding in (
        ("utf-8", "utf-8"),
        ("windows-1251", "cp1251"),
        ("cp1251", "cp1251"),
        ("koi8-r", "koi8-r"),
    ):
        if f"charset={marker}" in header or f'charset="{marker}"' in header:
            return raw.decode(encoding)
    for encoding in ("utf-8", "cp1251", "koi8-r"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError("Lib.ru HTML could not be decoded as UTF-8, CP1251, or KOI8-R")


def _author_name(page_title: str, url: str) -> str:
    for pattern in _AUTHOR_TITLE_PATTERNS:
        match = pattern.search(page_title)
        if match:
            return " ".join(match.group(1).split())
    slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return slug.replace("_", " ")


def _candidate_id(author_url: str, work_url: str) -> str:
    author_slug = urlparse(author_url).path.rstrip("/").rsplit("/", 1)[-1]
    file_stem = urlparse(work_url).path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    raw = f"libru-{author_slug}-{file_stem}".lower().replace("_", "-")
    return re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")


def _classify(title: str, context: str) -> tuple[str, str]:
    haystack = f"{title} {context}".casefold()
    if any(marker in haystack for marker in _EXCLUDE_MARKERS):
        return "exclude", "automatic: epistolary/correspondence"
    if any(marker in haystack for marker in _REVIEW_MARKERS):
        return "review", "automatic: non-fictional or editorial category requires review"
    if any(marker in haystack for marker in _INCLUDE_MARKERS):
        return "include", "automatic: literary category"
    return "review", "automatic: category could not be classified safely"


def discover_author_page(
    url: str,
    raw_html: bytes,
    *,
    language: str = "ru",
    original_language: str | None = None,
) -> SelectionManifest:
    """Builds a language-aware review selection from one Lib.ru author/catalog page."""
    canonical_url = url.rstrip("/") + "/"
    parser = _DocumentParser()
    parser.feed(decode_html(raw_html))
    author = _author_name(parser.page_title, canonical_url)
    works: list[SelectionWork] = []
    seen_urls: set[str] = set()
    for anchor in parser.work_anchors(canonical_url):
        if not anchor.label or anchor.href in seen_urls:
            continue
        seen_urls.add(anchor.href)
        decision, reason = _classify(anchor.label, anchor.context)
        year_match = _YEAR.search(anchor.context)
        context_casefold = anchor.context.casefold()
        genres = tuple(name for name in _GENRE_NAMES if name.casefold() in context_casefold)
        works.append(
            SelectionWork(
                id=_candidate_id(canonical_url, anchor.href),
                title=anchor.label,
                source_url=anchor.href,
                decision=decision,
                reason=reason,
                year=int(year_match.group(1)) if year_match else None,
                genres=genres,
            )
        )
    if not works:
        raise ValueError(f"No Lib.ru work pages discovered at {url}")
    return SelectionManifest(
        source_family="libru",
        source_url=canonical_url,
        author=author,
        language=language,
        original_language=original_language or language,
        category="literature",
        works=tuple(works),
    )
