from __future__ import annotations

from pathlib import Path
import tomllib
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
WORKS_DIR = ROOT / "works"
COLLECTIONS_DIR = ROOT / "collections"

ALLOWED_CATEGORIES = {"literature", "philosophy", "sacred_text"}
ALLOWED_ROLES = {"original", "human_translation", "machine_translation"}
ALLOWED_REVIEW_STATUS = {"candidate", "approved", "rejected"}
ALLOWED_RIGHTS_STATUS = {"review_required", "approved", "rejected"}


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_work(path: Path) -> tuple[str, bool]:
    data = load_toml(path)
    prefix = str(path.relative_to(ROOT))

    require(data.get("schema_version") == 1, f"{prefix}: unsupported schema_version")
    work_id = data.get("work_id")
    require(isinstance(work_id, str) and work_id, f"{prefix}: missing work_id")
    require(data.get("category") in ALLOWED_CATEGORIES, f"{prefix}: invalid category")
    require(data.get("review_status") in ALLOWED_REVIEW_STATUS, f"{prefix}: invalid review_status")
    require(isinstance(data.get("author"), str) and data["author"], f"{prefix}: missing author")
    require(isinstance(data.get("title"), str) and data["title"], f"{prefix}: missing title")
    require(isinstance(data.get("original_language"), str) and data["original_language"], f"{prefix}: missing original_language")

    versions = data.get("text_versions")
    require(isinstance(versions, list) and versions, f"{prefix}: at least one text version is required")

    version_ids: set[str] = set()
    for version in versions:
        version_id = version.get("id")
        require(isinstance(version_id, str) and version_id, f"{prefix}: text version missing id")
        require(version_id not in version_ids, f"{prefix}: duplicate text version id {version_id}")
        version_ids.add(version_id)
        require(version.get("role") in ALLOWED_ROLES, f"{prefix}: invalid text role for {version_id}")
        require(version.get("rights_status") in ALLOWED_RIGHTS_STATUS, f"{prefix}: invalid rights_status for {version_id}")
        require(isinstance(version.get("language"), str) and version["language"], f"{prefix}: missing language for {version_id}")
        uri = version.get("source_uri")
        require(isinstance(uri, str) and urlparse(uri).scheme in {"http", "https"}, f"{prefix}: invalid source_uri for {version_id}")
        for hash_field in ("artifact_sha256", "canonical_sha256"):
            value = version.get(hash_field)
            if value is not None:
                require(
                    isinstance(value, str)
                    and len(value) == 64
                    and all(character in "0123456789abcdefABCDEF" for character in value),
                    f"{prefix}: invalid {hash_field} for {version_id}",
                )
        download_uri = version.get("download_uri")
        if download_uri is not None:
            require(
                isinstance(download_uri, str) and urlparse(download_uri).scheme in {"http", "https"},
                f"{prefix}: invalid download_uri for {version_id}",
            )

    enabled = bool(data.get("enabled", False))
    if enabled:
        require(data.get("review_status") == "approved", f"{prefix}: enabled work must be approved")
        for version in versions:
            require(version.get("rights_status") == "approved", f"{prefix}: enabled version must have approved rights")
            locator = version.get("source_locator")
            require(isinstance(locator, str) and locator and "Candidate" not in locator, f"{prefix}: enabled version needs a pinned source locator")
            require(
                isinstance(version.get("artifact_sha256"), str),
                f"{prefix}: enabled version needs artifact_sha256",
            )
            require(
                isinstance(version.get("canonical_sha256"), str),
                f"{prefix}: enabled version needs canonical_sha256",
            )

    return work_id, enabled


def validate_registry() -> None:
    work_files = sorted(WORKS_DIR.glob("*.toml"))
    require(bool(work_files), "no work records found")

    work_ids: set[str] = set()
    enabled_count = 0
    for path in work_files:
        work_id, enabled = validate_work(path)
        require(work_id not in work_ids, f"duplicate work_id: {work_id}")
        work_ids.add(work_id)
        enabled_count += int(enabled)

    collection_files = sorted(COLLECTIONS_DIR.glob("*.toml"))
    require(bool(collection_files), "no collections found")
    referenced: set[str] = set()
    collection_ids: set[str] = set()
    for path in collection_files:
        data = load_toml(path)
        prefix = str(path.relative_to(ROOT))
        require(data.get("schema_version") == 1, f"{prefix}: unsupported schema_version")
        collection_id = data.get("id")
        require(isinstance(collection_id, str) and collection_id, f"{prefix}: missing id")
        require(collection_id not in collection_ids, f"duplicate collection id: {collection_id}")
        collection_ids.add(collection_id)
        works = data.get("works")
        require(isinstance(works, list), f"{prefix}: works must be a list")
        for work_id in works:
            require(work_id in work_ids, f"{prefix}: unknown work id {work_id}")
            referenced.add(work_id)

    missing = sorted(work_ids - referenced)
    require(not missing, f"work records missing from collections: {', '.join(missing)}")
    print(f"Corpus source registry is valid: {len(work_ids)} works, {len(collection_ids)} collections, {enabled_count} enabled.")


if __name__ == "__main__":
    validate_registry()
