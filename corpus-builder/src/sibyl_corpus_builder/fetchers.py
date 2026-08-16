from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .libru import discover_libru_artifact_candidates
from .source_registry import RegistryTextVersion

_USER_AGENT = "SibylCorpusBuilder/0.4 (+local build-time corpus preparation)"


@dataclass(frozen=True)
class FetchedSourceCandidate:
    """A downloaded source representation that may be normalized into canonical text."""

    kind: str
    raw: bytes
    resolved_uri: str


class _GutenbergTextLinkParser(HTMLParser):
    """Extracts plain-text download candidates from a Project Gutenberg work page."""

    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text: list[str] = []
        self.candidates: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        self._href = attributes.get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.candidates.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def _download(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/plain,text/html,application/xml,application/zip,*/*;q=0.5",
        },
    )
    # Network access is explicit build-time behavior selected through the CLI.
    with urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()


def _discover_gutenberg_text_uri(landing_uri: str) -> str:
    html = _download(landing_uri).decode("utf-8", errors="replace")
    parser = _GutenbergTextLinkParser()
    parser.feed(html)

    ranked: list[tuple[int, str]] = []
    for href, label in parser.candidates:
        lower_href = href.lower()
        lower_label = label.lower()
        if "plain text utf-8" in lower_label:
            ranked.append((0, href))
        elif lower_href.endswith(".txt.utf-8"):
            ranked.append((1, href))
        elif lower_href.endswith(".txt"):
            ranked.append((2, href))
    if not ranked:
        raise ValueError(
            "No plain-text UTF-8 download found on Project Gutenberg page: "
            f"{landing_uri}"
        )
    ranked.sort(key=lambda item: (item[0], item[1]))
    return urljoin(landing_uri, ranked[0][1])


def iter_text_version_candidates(version: RegistryTextVersion):
    """Returns source-family-specific acquisition candidates in deterministic fallback order."""
    if version.source_family == "project_gutenberg":
        resolved_uri = version.download_uri or _discover_gutenberg_text_uri(version.source_uri)
        yield FetchedSourceCandidate("txt", _download(resolved_uri), resolved_uri)
        return

    if version.source_family == "libru":
        if version.download_uri:
            raw = _download(version.download_uri)
            yield FetchedSourceCandidate("auto", raw, version.download_uri)
            return

        work_page = _download(version.source_uri)
        candidates = discover_libru_artifact_candidates(version.source_uri, work_page)
        for candidate in candidates:
            if candidate.kind == "html" and candidate.uri == version.source_uri:
                yield FetchedSourceCandidate("html", work_page, candidate.uri)
                continue
            try:
                raw = _download(candidate.uri)
            except Exception:  # noqa: BLE001 - unavailable candidate falls through to the next kind
                continue
            yield FetchedSourceCandidate(candidate.kind, raw, candidate.uri)
        return

    raise ValueError(
        f"No automatic fetcher for source family {version.source_family!r}. "
        "Use 'sibyl-corpus import-file' with a manually reviewed UTF-8 text artifact."
    )


def fetch_text_version_candidates(version: RegistryTextVersion) -> tuple[FetchedSourceCandidate, ...]:
    """Downloads candidate artifacts while preserving per-candidate failure information."""
    return tuple(iter_text_version_candidates(version))


def fetch_text_version(version: RegistryTextVersion) -> tuple[bytes, str]:
    """Downloads the first usable artifact candidate for a registered text version."""
    try:
        candidate = next(iter_text_version_candidates(version))
    except StopIteration as error:
        raise ValueError(f"No downloadable source artifact for {version.source_uri}") from error
    return candidate.raw, candidate.resolved_uri
