from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .libru import discover_libru_author_page
from .selection import SelectionManifest, write_selection

_USER_AGENT = "SibylCorpusBuilder/0.3 (+local build-time corpus discovery)"


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()


def discover_source(url: str) -> SelectionManifest:
    parsed = urlparse(url)
    host = parsed.netloc.casefold()
    if host in {"az.lib.ru", "lib.ru", "www.lib.ru"}:
        return discover_libru_author_page(url, _download(url))
    raise ValueError(f"No discovery adapter for URL: {url}")


def discover_to_file(url: str, output: Path) -> SelectionManifest:
    manifest = discover_source(url)
    write_selection(manifest, output)
    return manifest
