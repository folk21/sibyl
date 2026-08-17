"""Project Gutenberg acquisition adapter.

Pipeline position:

    registry text version -> THIS MODULE -> downloaded plain-text candidate
                          -> source normalization -> cached SourceArtifact

Gutenberg landing pages are inspected only when a concrete ``download_uri`` is not pinned.
The adapter prefers a UTF-8 plain-text artifact and performs no literary normalization itself.
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin

from ..._internal.http import download
from ..._internal.registry import RegistryTextVersion


@dataclass(frozen=True)
class FetchedSourceCandidate:
    """One downloaded source representation that can be normalized into canonical text."""

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
        self._href = dict(attrs).get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.candidates.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def _discover_text_uri(landing_uri: str) -> str:
    html = download(landing_uri, accept="text/html").decode("utf-8", errors="replace")
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


def iter_candidates(version: RegistryTextVersion):
    """Yields the single preferred Gutenberg plain-text acquisition candidate."""
    resolved_uri = version.download_uri or _discover_text_uri(version.source_uri)
    yield FetchedSourceCandidate("txt", download(resolved_uri), resolved_uri)
