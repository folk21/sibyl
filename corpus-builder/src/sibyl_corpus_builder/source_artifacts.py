from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil

from .normalization import canonicalize_text
from .source_registry import RegistryTextVersion, RegistryWork


@dataclass(frozen=True)
class SourceArtifact:
    work_id: str
    text_version_id: str
    directory: Path
    raw_sha256: str
    canonical_sha256: str
    canonical_text: str
    normalizer: str
    artifact_kind: str
    resolved_uri: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def artifact_directory(cache_dir: Path, work_id: str, text_version_id: str) -> Path:
    return cache_dir / work_id / text_version_id


def _artifact_kind_from_normalizer(normalizer: str) -> str:
    if normalizer == "libru_txt_v1":
        return "txt"
    if normalizer == "libru_html_v1":
        return "html"
    if normalizer == "libru_fb2_v1":
        return "fb2"
    if normalizer == "project_gutenberg_v1":
        return "txt"
    return "text"


def write_source_artifact(
    *,
    cache_dir: Path,
    work: RegistryWork,
    version: RegistryTextVersion,
    raw: bytes,
    resolved_uri: str,
    artifact_kind: str | None = None,
) -> SourceArtifact:
    canonical_text, normalizer = canonicalize_text(
        raw,
        version.source_family,
        work_title=work.title,
        artifact_kind=artifact_kind,
    )
    if not canonical_text.strip():
        raise ValueError("Canonical source text is empty")

    resolved_kind = _artifact_kind_from_normalizer(normalizer)
    raw_sha256 = sha256_bytes(raw)
    canonical_sha256 = sha256_text(canonical_text)
    if version.artifact_sha256 and version.artifact_sha256.lower() != raw_sha256:
        raise ValueError(
            f"Raw artifact SHA-256 mismatch for {work.work_id}/{version.id}: "
            f"expected {version.artifact_sha256}, got {raw_sha256}"
        )
    if version.canonical_sha256 and version.canonical_sha256.lower() != canonical_sha256:
        raise ValueError(
            f"Canonical text SHA-256 mismatch for {work.work_id}/{version.id}: "
            f"expected {version.canonical_sha256}, got {canonical_sha256}"
        )

    destination = artifact_directory(cache_dir, work.work_id, version.id)
    staging = destination.with_name(f".{destination.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        (staging / "raw.bin").write_bytes(raw)
        (staging / "canonical.txt").write_text(canonical_text, encoding="utf-8")
        metadata = {
            "schema_version": 2,
            "work_id": work.work_id,
            "text_version_id": version.id,
            "source_family": version.source_family,
            "source_uri": version.source_uri,
            "resolved_uri": resolved_uri,
            "artifact_kind": resolved_kind,
            "normalizer": normalizer,
            "raw_sha256": raw_sha256,
            "canonical_sha256": canonical_sha256,
            "raw_bytes": len(raw),
            "canonical_utf8_bytes": len(canonical_text.encode("utf-8")),
        }
        (staging / "artifact.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            shutil.rmtree(destination)
        staging.rename(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    return SourceArtifact(
        work_id=work.work_id,
        text_version_id=version.id,
        directory=destination,
        raw_sha256=raw_sha256,
        canonical_sha256=canonical_sha256,
        canonical_text=canonical_text,
        normalizer=normalizer,
        artifact_kind=resolved_kind,
        resolved_uri=resolved_uri,
    )


def read_source_artifact(cache_dir: Path, work_id: str, text_version_id: str) -> SourceArtifact:
    directory = artifact_directory(cache_dir, work_id, text_version_id)
    metadata_path = directory / "artifact.json"
    canonical_path = directory / "canonical.txt"
    raw_path = directory / "raw.bin"
    if not metadata_path.is_file() or not canonical_path.is_file() or not raw_path.is_file():
        raise ValueError(f"Incomplete source artifact cache: {directory}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw = raw_path.read_bytes()
    canonical_text = canonical_path.read_text(encoding="utf-8")
    raw_sha256 = sha256_bytes(raw)
    canonical_sha256 = sha256_text(canonical_text)
    if raw_sha256 != metadata["raw_sha256"] or canonical_sha256 != metadata["canonical_sha256"]:
        raise ValueError(f"Cached source artifact checksum mismatch: {directory}")
    normalizer = str(metadata["normalizer"])
    return SourceArtifact(
        work_id=work_id,
        text_version_id=text_version_id,
        directory=directory,
        raw_sha256=raw_sha256,
        canonical_sha256=canonical_sha256,
        canonical_text=canonical_text,
        normalizer=normalizer,
        artifact_kind=str(metadata.get("artifact_kind") or _artifact_kind_from_normalizer(normalizer)),
        resolved_uri=str(metadata["resolved_uri"]),
    )
