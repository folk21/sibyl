"""Prepared-source materialization: the final source-ingestion stage.

Pipeline position:

    acquired + normalized SourceArtifact values
                    -> THIS MODULE
                    -> deterministic prepared source directory
                    -> corpus-core ``load_prepared_sources``
                       -> automatic build OR LLM curation

Preparation does not split passages, generate embeddings, or perform retrieval. Its job is to
materialize exact canonical text plus provenance into a stable input boundary shared by later
features.
"""

import json
from pathlib import Path

from sibyl_corpus_core.atomic import staging_directory

from .acquisition import selection_registry_models
from .artifacts import read_source_artifact
from .registry import load_registry_work, require_usable_source
from .selection import load_selection


def prepare_registry_sources(
    *,
    registry_dir: Path,
    cache_dir: Path,
    work_ids: list[str],
    output_dir: Path,
    allow_unapproved: bool,
) -> None:
    """Materializes cached registry artifacts as deterministic canonical source documents."""
    if not work_ids:
        raise ValueError("At least one --work is required")

    entries: list[dict[str, object]] = []
    with staging_directory(output_dir) as staging:
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
            json.dumps({"schema_version": 2, "works": entries}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )


def prepare_selection_sources(*, selection_path: Path, cache_dir: Path, output_dir: Path) -> None:
    """Materializes acquired selection items into the same shared prepared-source boundary."""
    manifest = load_selection(selection_path)
    included = manifest.included()
    if not included:
        raise ValueError("Selection has no works with decision = 'include'")

    entries: list[dict[str, object]] = []
    with staging_directory(output_dir) as staging:
        for selected_work in included:
            work, version = selection_registry_models(manifest, selected_work)
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
