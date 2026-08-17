"""Source acquisition orchestration for registry records and reviewed selections.

Pipeline position:

    reviewed selection / registry text version
                    -> THIS MODULE
                    -> source adapter candidates
                    -> artifact normalization/cache
                    -> preparation

This module coordinates retries/fallbacks and per-work isolation. Source-family parsing lives in
``sources.adapters``; artifact persistence lives in ``artifacts.py``.
"""

from pathlib import Path

from ..models import SelectionManifest, SelectionWork
from .adapters import iter_text_version_candidates
from .artifacts import SourceArtifact, write_source_artifact
from .registry import (
    RegistryTextVersion,
    RegistryWork,
    load_registry_work,
    require_usable_source,
)
from .reports import AcquisitionItem, AcquisitionReport, write_acquisition_report
from .selection import load_selection


def selection_registry_models(
    manifest: SelectionManifest, selected_work: SelectionWork
) -> tuple[RegistryWork, RegistryTextVersion]:
    """Builds temporary registry-shaped models for a reviewed Lib.ru selection item."""
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


def _write_first_valid_candidate(*, cache_dir: Path, work, version, candidates) -> SourceArtifact:
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
    """Imports a manually reviewed local UTF-8 artifact into the normal source cache."""
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


def acquire_selection(
    *, selection_path: Path, cache_dir: Path, report_path: Path | None = None
) -> AcquisitionReport:
    """Acquires only ``include`` items and records per-work failures without aborting early."""
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

        work, version = selection_registry_models(manifest, selected_work)
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
