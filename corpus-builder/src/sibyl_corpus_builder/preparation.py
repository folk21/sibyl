from dataclasses import dataclass
import json
from pathlib import Path
import shutil

from .fetchers import FetchedSourceCandidate, iter_text_version_candidates
from .source_artifacts import SourceArtifact, read_source_artifact, write_source_artifact
from .source_registry import load_registry_work, require_usable_source


@dataclass(frozen=True)
class AcquisitionItem:
    """Records the outcome and artifact metadata for one selected work."""

    work_id: str
    title: str
    status: str
    artifact_kind: str | None = None
    resolved_uri: str | None = None
    normalizer: str | None = None
    error: str | None = None
    decision: str | None = None


@dataclass(frozen=True)
class AcquisitionReport:
    """Groups acquired, failed, and skipped work outcomes for a batch run."""

    selection_path: Path
    items: tuple[AcquisitionItem, ...]

    @property
    def acquired(self) -> tuple[AcquisitionItem, ...]:
        return tuple(item for item in self.items if item.status == "acquired")

    @property
    def failed(self) -> tuple[AcquisitionItem, ...]:
        return tuple(item for item in self.items if item.status == "failed")

    @property
    def skipped(self) -> tuple[AcquisitionItem, ...]:
        return tuple(item for item in self.items if item.status == "skipped")


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def write_acquisition_report(report: AcquisitionReport, path: Path) -> None:
    """Persists a deterministic batch acquisition report for later review and retry."""
    lines = [
        "schema_version = 1",
        f"selection = {_quote(str(report.selection_path))}",
        f"acquired_count = {len(report.acquired)}",
        f"failed_count = {len(report.failed)}",
        f"skipped_count = {len(report.skipped)}",
    ]
    for item in report.items:
        lines.extend(
            [
                "",
                "[[items]]",
                f"work_id = {_quote(item.work_id)}",
                f"title = {_quote(item.title)}",
                f"status = {_quote(item.status)}",
            ]
        )
        if item.decision is not None:
            lines.append(f"decision = {_quote(item.decision)}")
        if item.artifact_kind is not None:
            lines.append(f"artifact_kind = {_quote(item.artifact_kind)}")
        if item.resolved_uri is not None:
            lines.append(f"resolved_uri = {_quote(item.resolved_uri)}")
        if item.normalizer is not None:
            lines.append(f"normalizer = {_quote(item.normalizer)}")
        if item.error is not None:
            lines.append(f"error = {_quote(item.error)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_first_valid_candidate(
    *, cache_dir: Path, work, version, candidates
) -> SourceArtifact:
    errors: list[str] = []
    for candidate in candidates:
        try:
            return write_source_artifact(
                cache_dir=cache_dir,
                work=work,
                version=version,
                raw=candidate.raw,
                resolved_uri=candidate.resolved_uri,
                artifact_kind=None if candidate.kind == "auto" else candidate.kind,
            )
        except Exception as error:  # noqa: BLE001 - source fallback is intentional
            errors.append(f"{candidate.kind} {candidate.resolved_uri}: {error}")
    detail = "; ".join(errors) if errors else "no candidates"
    raise ValueError(f"No usable source artifact for {work.work_id}: {detail}")


def fetch_registry_source(
    *,
    registry_dir: Path,
    cache_dir: Path,
    work_id: str,
    version_id: str | None,
    allow_unapproved: bool,
) -> Path:
    """Acquires and caches one concrete registry text version after approval checks."""
    work = load_registry_work(registry_dir, work_id)
    version = work.text_version(version_id)
    require_usable_source(work, version, allow_unapproved=allow_unapproved)
    artifact = _write_first_valid_candidate(
        cache_dir=cache_dir,
        work=work,
        version=version,
        candidates=iter_text_version_candidates(version),
    )
    return artifact.directory


def import_registry_source(
    *,
    registry_dir: Path,
    cache_dir: Path,
    work_id: str,
    version_id: str | None,
    file_path: Path,
    allow_unapproved: bool,
) -> Path:
    """Imports a reviewed local UTF-8 artifact as a concrete registry source version."""
    work = load_registry_work(registry_dir, work_id)
    version = work.text_version(version_id)
    require_usable_source(work, version, allow_unapproved=allow_unapproved)
    if not file_path.is_file():
        raise ValueError(f"Import file does not exist: {file_path}")
    artifact = write_source_artifact(
        cache_dir=cache_dir,
        work=work,
        version=version,
        raw=file_path.read_bytes(),
        resolved_uri=file_path.resolve().as_uri(),
    )
    return artifact.directory


def prepare_registry_sources(
    *,
    registry_dir: Path,
    cache_dir: Path,
    work_ids: list[str],
    output_dir: Path,
    allow_unapproved: bool,
) -> None:
    """Materializes cached registry artifacts as deterministic builder source documents."""
    if not work_ids:
        raise ValueError("At least one --work is required")

    output_dir = output_dir.resolve()
    staging = output_dir.with_name(f".{output_dir.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    entries: list[dict[str, object]] = []

    try:
        for work_id in work_ids:
            work = load_registry_work(registry_dir, work_id)
            for version in work.text_versions:
                require_usable_source(work, version, allow_unapproved=allow_unapproved)
                artifact = read_source_artifact(cache_dir, work.work_id, version.id)
                if (
                    version.artifact_sha256
                    and version.artifact_sha256.lower() != artifact.raw_sha256
                ):
                    raise ValueError(
                        "Registry raw SHA-256 does not match cache for "
                        f"{work.work_id}/{version.id}"
                    )
                if (
                    version.canonical_sha256
                    and version.canonical_sha256.lower() != artifact.canonical_sha256
                ):
                    raise ValueError(
                        "Registry canonical SHA-256 does not match cache for "
                        f"{work.work_id}/{version.id}"
                    )

                file_name = f"{version.id}.txt"
                (staging / file_name).write_text(artifact.canonical_text, encoding="utf-8")
                entries.append(
                    {
                        "id": work.work_id,
                        "text_version_id": version.id,
                        "author": work.author,
                        "title": work.title,
                        "file": file_name,
                        "source_name": version.source_name,
                        "language": version.language,
                        "original_language": work.original_language,
                        "category": work.category,
                        "text_role": version.role,
                        "translator": version.translator,
                        "translation_provider": version.translation_provider,
                        "translation_model": version.translation_model,
                        "source_uri": version.source_uri,
                        "source_locator": version.source_locator,
                        "source_artifact_sha256": artifact.raw_sha256,
                        "canonical_text_sha256": artifact.canonical_sha256,
                        "rights_status": version.rights_status,
                        "rights_jurisdiction": version.rights_jurisdiction,
                        "provenance": version.provenance,
                    }
                )

        (staging / "manifest.json").write_text(
            json.dumps(
                {"schema_version": 2, "works": entries},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging.rename(output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _selection_registry_models(manifest, selected_work):
    from .source_registry import RegistryTextVersion, RegistryWork

    version_id = f"{selected_work.id}-libru"
    version = RegistryTextVersion(
        id=version_id,
        language=manifest.language,
        role="original",
        source_family=manifest.source_family,
        source_name="Lib.ru / Классика",
        source_uri=selected_work.source_url,
        source_locator=(
            "Lib.ru work page; acquisition prefers TXT, then reviewed HTML extraction, then FB2. "
            "Pin hashes before approval."
        ),
        rights_status="review_required",
        rights_jurisdiction="RU",
        provenance=f"Discovered from {manifest.source_url}",
    )
    work = RegistryWork(
        work_id=selected_work.id,
        author=manifest.author,
        title=selected_work.title,
        category=manifest.category,
        original_language=manifest.original_language,
        enabled=False,
        review_status="candidate",
        text_versions=(version,),
    )
    return work, version


def acquire_selection(
    *, selection_path: Path, cache_dir: Path, report_path: Path | None = None
) -> AcquisitionReport:
    """Acquires only explicitly included catalog works and isolates per-work failures."""
    from .selection import load_selection

    manifest = load_selection(selection_path)
    if manifest.source_family != "libru":
        raise ValueError(f"Selection acquisition is not implemented for {manifest.source_family!r}")
    if not manifest.included():
        raise ValueError("Selection has no works with decision = 'include'")

    items: list[AcquisitionItem] = []
    for selected_work in manifest.works:
        if selected_work.decision != "include":
            items.append(
                AcquisitionItem(
                    work_id=selected_work.id,
                    title=selected_work.title,
                    status="skipped",
                    decision=selected_work.decision,
                )
            )
            continue

        work, version = _selection_registry_models(manifest, selected_work)
        try:
            artifact = _write_first_valid_candidate(
                cache_dir=cache_dir,
                work=work,
                version=version,
                candidates=iter_text_version_candidates(version),
            )
            items.append(
                AcquisitionItem(
                    work_id=selected_work.id,
                    title=selected_work.title,
                    status="acquired",
                    decision="include",
                    artifact_kind=artifact.artifact_kind,
                    resolved_uri=artifact.resolved_uri,
                    normalizer=artifact.normalizer,
                )
            )
        except Exception as error:  # noqa: BLE001 - batch acquisition must isolate works
            items.append(
                AcquisitionItem(
                    work_id=selected_work.id,
                    title=selected_work.title,
                    status="failed",
                    decision="include",
                    error=str(error),
                )
            )

    report = AcquisitionReport(selection_path=selection_path, items=tuple(items))
    resolved_report = report_path or selection_path.with_name(
        f"{selection_path.stem}-acquire-report.toml"
    )
    write_acquisition_report(report, resolved_report)
    return report


def prepare_selection_sources(*, selection_path: Path, cache_dir: Path, output_dir: Path) -> None:
    """Converts acquired selection artifacts into deterministic builder input files."""
    from .selection import load_selection

    manifest = load_selection(selection_path)
    included = manifest.included()
    if not included:
        raise ValueError("Selection has no works with decision = 'include'")

    output_dir = output_dir.resolve()
    staging = output_dir.with_name(f".{output_dir.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    entries: list[dict[str, object]] = []

    try:
        for selected_work in included:
            work, version = _selection_registry_models(manifest, selected_work)
            artifact = read_source_artifact(cache_dir, work.work_id, version.id)
            output_work_id = selected_work.registry_work_id or work.work_id
            output_version_id = f"{output_work_id}-libru"
            file_name = f"{output_version_id}.txt"
            (staging / file_name).write_text(artifact.canonical_text, encoding="utf-8")
            entries.append(
                {
                    "id": output_work_id,
                    "text_version_id": output_version_id,
                    "author": work.author,
                    "title": work.title,
                    "file": file_name,
                    "source_name": version.source_name,
                    "language": version.language,
                    "original_language": work.original_language,
                    "category": work.category,
                    "text_role": version.role,
                    "translator": None,
                    "translation_provider": None,
                    "translation_model": None,
                    "source_uri": version.source_uri,
                    "source_locator": (
                        f"Lib.ru {artifact.artifact_kind} artifact resolved from work page; "
                        f"normalizer={artifact.normalizer}"
                    ),
                    "source_artifact_sha256": artifact.raw_sha256,
                    "canonical_text_sha256": artifact.canonical_sha256,
                    "rights_status": version.rights_status,
                    "rights_jurisdiction": version.rights_jurisdiction,
                    "provenance": version.provenance,
                }
            )

        (staging / "manifest.json").write_text(
            json.dumps({"schema_version": 2, "works": entries}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging.rename(output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
