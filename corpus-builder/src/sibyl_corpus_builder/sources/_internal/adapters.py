"""Central dispatch between source-family-neutral workflows and concrete adapters.

The rest of ``sources`` calls this module instead of scattering ``if source_family == ...``
branches across acquisition and normalization. Adding a source family should normally require
one adapter package plus one explicit mapping here.
"""

from urllib.parse import urlparse

from ..adapters.gutenberg.fetch import FetchedSourceCandidate as GutenbergCandidate
from ..adapters.gutenberg.fetch import iter_candidates as iter_gutenberg_candidates
from ..adapters.gutenberg.normalize import canonicalize as canonicalize_gutenberg
from ..adapters.libru.discovery import discover_author_page as discover_libru_author_page
from ..adapters.libru.fetch import FetchedSourceCandidate as LibRuCandidate
from ..adapters.libru.fetch import iter_candidates as iter_libru_candidates
from ..adapters.libru.normalize import canonicalize as canonicalize_libru
from ..models import SelectionManifest
from .http import download
from .registry import RegistryTextVersion

FetchedCandidate = GutenbergCandidate | LibRuCandidate


def discover_source(
    url: str,
    *,
    language: str | None = None,
    original_language: str | None = None,
) -> SelectionManifest:
    """Discovers a review manifest with optional text/original-language overrides."""
    host = urlparse(url).netloc.casefold()
    if host in {"az.lib.ru", "lib.ru", "www.lib.ru"}:
        return discover_libru_author_page(
            url,
            download(url, accept="text/html"),
            language=language or "ru",
            original_language=original_language,
        )
    raise ValueError(f"No discovery adapter for URL: {url}")


def iter_text_version_candidates(version: RegistryTextVersion):
    """Yields acquisition candidates from the adapter owning ``version.source_family``."""
    if version.source_family == "project_gutenberg":
        yield from iter_gutenberg_candidates(version)
        return
    if version.source_family == "libru":
        yield from iter_libru_candidates(version)
        return
    raise ValueError(
        f"No automatic fetcher for source family {version.source_family!r}. "
        "Use 'sibyl-corpus import-file' with a manually reviewed UTF-8 text artifact."
    )


def canonicalize_source(
    raw: bytes,
    source_family: str,
    *,
    work_title: str | None = None,
    artifact_kind: str | None = None,
) -> tuple[str, str]:
    """Returns canonical text plus normalizer version for one acquired source artifact."""
    if source_family == "libru":
        return canonicalize_libru(raw, work_title=work_title, artifact_kind=artifact_kind)

    text = _decode_utf8(raw)
    if source_family == "project_gutenberg":
        return canonicalize_gutenberg(text), "project_gutenberg_v1"
    return _trim_plain_text(text), "plain_text_v1"


def _decode_utf8(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Source artifact is not valid UTF-8; convert it explicitly before import"
        ) from error


def _trim_plain_text(text: str) -> str:
    from sibyl_corpus_core.text import normalize_newlines, trim_blank_edge_lines

    return trim_blank_edge_lines(normalize_newlines(text))
