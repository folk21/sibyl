"""Validation primitives for generated translation metadata and identities."""

import re

_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")
_BUNDLE_ID = re.compile(r"tb_[0-9a-f]{20}")
_LANGUAGE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def validate_id(value: object, label: str) -> str:
    """Validates stable local translation and source-curation identifiers."""
    result = str(value)
    if not _ID.fullmatch(result):
        raise ValueError(f"Invalid {label}: {result!r}")
    return result


def validate_bundle_id(value: object) -> str:
    """Validates deterministic translation-bundle identifiers."""
    result = str(value)
    if not _BUNDLE_ID.fullmatch(result):
        raise ValueError(f"Invalid translation source_bundle_id: {result!r}")
    return result


def validate_language(value: object, label: str = "target_language") -> str:
    """Validates a compact BCP-47-like language tag used by corpus metadata."""
    result = str(value).strip()
    if not _LANGUAGE.fullmatch(result):
        raise ValueError(f"Invalid {label}: {result!r}")
    return result


def validate_sha256(value: object, label: str) -> str:
    """Validates a lowercase exact-text SHA-256 value."""
    result = str(value).lower()
    if not _SHA256.fullmatch(result):
        raise ValueError(f"Invalid {label} SHA-256: {value!r}")
    return result


def require_nonblank(value: object, label: str) -> str:
    """Returns one required metadata string without changing its stored wording."""
    result = str(value)
    if not result.strip():
        raise ValueError(f"{label} must not be blank")
    return result
