"""Lib.ru work-artifact discovery and acquisition.

Pipeline position:

    reviewed Lib.ru work -> THIS MODULE -> TXT / HTML / FB2 candidates
                                         -> normalization -> cached SourceArtifact

The fallback order is deliberately TXT -> work-page HTML -> FB2. Candidate download failures
are isolated so malformed/unavailable representations do not prevent trying the next format.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from time import sleep
from urllib.parse import urljoin, urlparse

from ..._internal.http import download
from ..._internal.registry import RegistryTextVersion
from .discovery import decode_html

_DIRECT_TXT_ATTEMPT_DELAYS_SECONDS = (0.4, 1.0, 2.0, 4.0)


@dataclass(frozen=True)
class LibRuArtifactCandidate:
    """One ordered Lib.ru artifact URI discovered from a work page."""

    kind: str
    uri: str


@dataclass(frozen=True)
class FetchedSourceCandidate:
    """One downloaded source representation ready for source-specific normalization."""

    kind: str
    raw: bytes
    resolved_uri: str


class _WorkLinkParser(HTMLParser):
    """Collects links from a Lib.ru work page to discover TXT and FB2 alternatives."""

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


def discover_artifact_candidates(
    work_url: str, raw_html: bytes
) -> tuple[LibRuArtifactCandidate, ...]:
    """Discovers deterministic TXT -> HTML -> FB2 candidate URIs for one work page."""
    parser = _WorkLinkParser()
    parser.feed(decode_html(raw_html))

    txt_links: list[str] = []
    fb2_links: list[str] = []
    for href, label in parser.links:
        absolute = urljoin(work_url, href)
        lower_href = href.casefold()
        lower_label = label.casefold().replace(" ", "")
        if (
            lower_href.endswith(".txt")
            or lower_label.startswith("txt(")
            or label.casefold() == "txt"
        ):
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
    """Returns the first FB2 candidate URI for diagnostics and focused tests."""
    for candidate in discover_artifact_candidates(work_url, raw_html):
        if candidate.kind == "fb2":
            return candidate.uri
    raise ValueError(f"No FB2 download link found on Lib.ru work page: {work_url}")


def _iter_direct_txt_candidates(uri: str):
    """Yields paced retries because Lib.ru sometimes serves transient HTML for TXT URLs."""
    for delay_seconds in _DIRECT_TXT_ATTEMPT_DELAYS_SECONDS:
        sleep(delay_seconds)
        raw = download(
            uri,
            accept="text/plain,text/html;q=0.9,*/*;q=0.1",
        )
        yield FetchedSourceCandidate("txt", raw, uri)


def iter_candidates(version: RegistryTextVersion):
    """Downloads direct Lib.ru TXT artifacts or work-page fallbacks in deterministic order."""
    if version.download_uri:
        if urlparse(version.download_uri).path.casefold().endswith(".txt"):
            yield from _iter_direct_txt_candidates(version.download_uri)
        else:
            raw = download(version.download_uri)
            yield FetchedSourceCandidate("auto", raw, version.download_uri)
        return

    source_path = urlparse(version.source_uri).path.casefold()
    if source_path.endswith(".txt"):
        yield from _iter_direct_txt_candidates(version.source_uri)
        return

    work_page = download(version.source_uri, accept="text/html")
    candidates = discover_artifact_candidates(version.source_uri, work_page)
    for candidate in candidates:
        if candidate.kind == "html" and candidate.uri == version.source_uri:
            yield FetchedSourceCandidate("html", work_page, candidate.uri)
            continue
        try:
            raw = download(candidate.uri)
        except Exception:  # noqa: BLE001 - unavailable candidate intentionally falls through
            continue
        yield FetchedSourceCandidate(candidate.kind, raw, candidate.uri)
