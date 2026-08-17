"""Stable SHA-256 helpers for corpus identities and exact-text verification."""

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    """Returns the lowercase SHA-256 digest for exact bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Returns the SHA-256 digest of the exact UTF-8 representation of ``text``."""
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    """Streams a file into SHA-256 without loading large model/source files into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
