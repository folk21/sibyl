"""Explicit build-time HTTP primitive shared only by source adapters.

Network access in Sibyl corpus tooling is always selected by an explicit CLI command. Keeping
this helper under ``sources._internal`` prevents unrelated build/curation features from
acquiring an accidental network dependency.
"""

from urllib.request import Request, urlopen

_USER_AGENT = "SibylCorpusBuilder/0.6 (+local build-time corpus preparation)"


def download(url: str, *, accept: str = "*/*") -> bytes:
    """Downloads one source artifact with the corpus-builder user agent."""
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": accept})
    with urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()
