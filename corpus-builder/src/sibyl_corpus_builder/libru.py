import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from .selection import SelectionManifest, SelectionWork

_AUTHOR_TITLE_PATTERNS = (
    re.compile(r"Lib\.ru/Классика[:.]\s*(.+?)\.\s*Полное собрание", re.I),
    re.compile(r"Lib\.Ru\s*/\s*Классика:\s*(.+?)(?::|$)", re.I),
)
_YEAR = re.compile(r"\[([12]\d{3})\]")
_TEXT_PAGE = re.compile(r"^text_[^/?#]+\.shtml$", re.I)

_INCLUDE_MARKERS = (
    "проза",
    "роман",
    "повесть",
    "рассказ",
    "поэзия",
    "драматургия",
    "сказки",
    "детская",
)
_REVIEW_MARKERS = (
    "публицистика",
    "критика",
    "мемуары",
    "философия",
    "религия",
    "переводы",
    "рукопис",
    "наброс",
    "записн",
    "дневник",
    "dubia",
)
_EXCLUDE_MARKERS = (
    "эпистоляр",
    "переписк",
    "письма",
    "письмо ",
    "из писем",
    "на письмах",
)
_GENRE_NAMES = (
    "Проза",
    "Романы",
    "Поэзия",
    "Драматургия",
    "Сказки",
    "Детская",
    "Публицистика",
    "Критика",
    "Мемуары",
    "Философия",
    "Религия",
    "Переводы",
    "Эпистолярий",
)


@dataclass(frozen=True)
class _Anchor:
    """Captures one parsed Lib.ru link and its surrounding catalog metadata."""

    href: str
    label: str
    context: str


@dataclass(frozen=True)
class LibRuArtifactCandidate:
    """Describes one ordered Lib.ru artifact candidate for resilient acquisition."""

    kind: str
    uri: str


class _DocumentParser(HTMLParser):
    """Collects page metadata and links from a Lib.ru HTML document."""

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
            if not _TEXT_PAGE.fullmatch(file_name):
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
            context_parts: list[str] = []
            for _node_kind, _node_href, node_text in self._nodes[index + 1 : end]:
                if node_text:
                    context_parts.append(node_text)
            anchors.append(
                _Anchor(
                    href=urljoin(canonical_base, href),
                    label=label,
                    context=" ".join(" ".join(context_parts).split()),
                )
            )
        return anchors


def decode_libru_html(raw: bytes) -> str:
    header = raw[:8192].decode("ascii", errors="ignore").casefold()
    declared = (
        ("utf-8", "utf-8"),
        ("windows-1251", "cp1251"),
        ("cp1251", "cp1251"),
        ("koi8-r", "koi8-r"),
    )
    for marker, encoding in declared:
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


def discover_libru_author_page(url: str, raw_html: bytes) -> SelectionManifest:
    canonical_url = url.rstrip("/") + "/"
    parser = _DocumentParser()
    parser.feed(decode_libru_html(raw_html))
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
        language="ru",
        original_language="ru",
        category="literature",
        works=tuple(works),
    )


class _WorkLinkParser(HTMLParser):
    """Extracts candidate work links and sections from a Lib.ru author catalog page."""

    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, " ".join(" ".join(self._text).split())))
            self._href = None
            self._text = []


def _derived_txt_uri(work_url: str) -> str | None:
    parsed = urlparse(work_url)
    if not parsed.path.lower().endswith(".shtml"):
        return None
    return parsed._replace(path=parsed.path[:-6] + ".txt").geturl()


def discover_libru_artifact_candidates(
    work_url: str, raw_html: bytes
) -> tuple[LibRuArtifactCandidate, ...]:
    parser = _WorkLinkParser()
    parser.feed(decode_libru_html(raw_html))

    txt_links: list[str] = []
    fb2_links: list[str] = []
    for href, label in parser.links:
        absolute = urljoin(work_url, href)
        lower_href = href.casefold()
        lower_label = label.casefold().replace(" ", "")
        if lower_href.endswith(".txt") or lower_label.startswith("txt(") or label.casefold() == "txt":
            txt_links.append(absolute)
        if "скачать fb2" in label.casefold() or "fb2" in label.casefold() or ".fb2" in lower_href:
            fb2_links.append(absolute)

    derived = _derived_txt_uri(work_url)
    if derived is not None:
        txt_links.append(derived)

    candidates: list[LibRuArtifactCandidate] = []
    seen: set[str] = set()
    for uri in txt_links:
        if uri not in seen:
            candidates.append(LibRuArtifactCandidate(kind="txt", uri=uri))
            seen.add(uri)

    if work_url not in seen:
        candidates.append(LibRuArtifactCandidate(kind="html", uri=work_url))
        seen.add(work_url)

    for uri in fb2_links:
        if uri not in seen:
            candidates.append(LibRuArtifactCandidate(kind="fb2", uri=uri))
            seen.add(uri)

    return tuple(candidates)


def discover_fb2_uri(work_url: str, raw_html: bytes) -> str:
    candidates = discover_libru_artifact_candidates(work_url, raw_html)
    for candidate in candidates:
        if candidate.kind == "fb2":
            return candidate.uri
    raise ValueError(f"No FB2 download link found on Lib.ru work page: {work_url}")
