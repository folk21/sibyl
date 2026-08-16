from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class RegistryTextVersion:
    """One concrete source text version with provenance, rights, and artifact metadata."""

    id: str
    language: str
    role: str
    source_family: str
    source_name: str
    source_uri: str
    source_locator: str
    rights_status: str
    rights_jurisdiction: str
    provenance: str
    translator: str | None = None
    translation_provider: str | None = None
    translation_model: str | None = None
    download_uri: str | None = None
    artifact_sha256: str | None = None
    canonical_sha256: str | None = None


@dataclass(frozen=True)
class RegistryWork:
    """A registry work and its reviewed concrete text versions."""

    work_id: str
    author: str
    title: str
    category: str
    original_language: str
    enabled: bool
    review_status: str
    text_versions: tuple[RegistryTextVersion, ...]

    def text_version(self, version_id: str | None = None) -> RegistryTextVersion:
        """Resolve a text version, requiring an ID when multiple versions exist."""
        if version_id is None:
            if len(self.text_versions) != 1:
                raise ValueError(
                    f"Work {self.work_id} has multiple text versions; --version is required"
                )
            return self.text_versions[0]
        for version in self.text_versions:
            if version.id == version_id:
                return version
        raise ValueError(f"Unknown text version {version_id!r} for work {self.work_id}")


def load_registry_work(registry_dir: Path, work_id: str) -> RegistryWork:
    """Loads one permanent source-registry record into typed immutable models."""
    path = registry_dir / "works" / f"{work_id}.toml"
    if not path.is_file():
        raise ValueError(f"Unknown registry work: {work_id}")
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    versions = tuple(
        RegistryTextVersion(
            id=str(item["id"]),
            language=str(item["language"]),
            role=str(item["role"]),
            source_family=str(item["source_family"]),
            source_name=str(item["source_name"]),
            source_uri=str(item["source_uri"]),
            source_locator=str(item.get("source_locator", "")),
            rights_status=str(item["rights_status"]),
            rights_jurisdiction=str(item.get("rights_jurisdiction", "")),
            provenance=str(item.get("provenance", "")),
            translator=item.get("translator"),
            translation_provider=item.get("translation_provider"),
            translation_model=item.get("translation_model"),
            download_uri=item.get("download_uri"),
            artifact_sha256=item.get("artifact_sha256"),
            canonical_sha256=item.get("canonical_sha256"),
        )
        for item in raw["text_versions"]
    )
    return RegistryWork(
        work_id=str(raw["work_id"]),
        author=str(raw["author"]),
        title=str(raw["title"]),
        category=str(raw["category"]),
        original_language=str(raw["original_language"]),
        enabled=bool(raw.get("enabled", False)),
        review_status=str(raw["review_status"]),
        text_versions=versions,
    )


def require_usable_source(
    work: RegistryWork,
    version: RegistryTextVersion,
    *,
    allow_unapproved: bool,
) -> None:
    """Enforces approval and rights requirements unless local review is explicitly allowed."""
    if allow_unapproved:
        return
    if not work.enabled or work.review_status != "approved" or version.rights_status != "approved":
        raise ValueError(
            f"Source {work.work_id}/{version.id} is not approved and enabled. "
            "Use --allow-unapproved only for local review/preparation; do not publish that output."
        )
