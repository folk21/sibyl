"""Permanent registry registration for reviewed acquired selections.

Registration is deliberately later than discovery/acquisition. It converts a locally reviewed
selection plus pinned artifact hashes into disabled candidate records under ``corpus-sources``;
it never approves/enables the resulting source versions automatically.
"""

import re
from pathlib import Path

from .acquisition import selection_registry_models
from .artifacts import read_source_artifact
from .selection import load_selection


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "selection"


def _work_toml(manifest, selected_work, artifact) -> str:
    work_id = selected_work.registry_work_id or selected_work.id
    _work, version = selection_registry_models(manifest, selected_work)
    version_id = f"{work_id}-libru"
    rights_notes = (
        "Author public-domain status does not by itself approve this concrete electronic edition; "
        "review source reuse terms before enabling."
    )
    direct_txt = selected_work.source_url.casefold().split("?", 1)[0].endswith(".txt")
    provenance = (
        f"Discovered from {manifest.source_url}; acquired directly from the Lib.ru catalog as "
        f"{artifact.artifact_kind} and normalized with {artifact.normalizer}."
        if direct_txt
        else (
            f"Discovered from {manifest.source_url}; acquired from the Lib.ru work page as "
            f"{artifact.artifact_kind} and normalized with {artifact.normalizer}."
        )
    )
    source_locator = (
        f"Lib.ru direct {artifact.artifact_kind.upper()} catalog artifact; "
        f"normalizer={artifact.normalizer}."
        if direct_txt
        else (
            f"Lib.ru work page; resolved {artifact.artifact_kind} artifact; "
            f"normalizer={artifact.normalizer}."
        )
    )
    lines = [
        "schema_version = 1",
        f"work_id = {_quote(work_id)}",
        f"author = {_quote(manifest.author)}",
        f"title = {_quote(selected_work.title)}",
        f"category = {_quote(manifest.category)}",
        f"original_language = {_quote(manifest.original_language)}",
        "enabled = false",
        'review_status = "candidate"',
        (
            'russian_display_policy = "source_text"'
            if manifest.language == "ru"
            else 'russian_display_policy = "build_time_machine_translation"'
        ),
        "",
        "[[text_versions]]",
        f"id = {_quote(version_id)}",
        f"language = {_quote(manifest.language)}",
        'role = "original"',
        'source_family = "libru"',
        f"source_name = {_quote(version.source_name)}",
        f"source_uri = {_quote(selected_work.source_url)}",
        f"source_locator = {_quote(source_locator)}",
        f"download_uri = {_quote(artifact.resolved_uri)}",
        'rights_status = "review_required"',
        'rights_jurisdiction = "RU"',
        f"rights_notes = {_quote(rights_notes)}",
        f"provenance = {_quote(provenance)}",
        f"artifact_sha256 = {_quote(artifact.raw_sha256)}",
        f"canonical_sha256 = {_quote(artifact.canonical_sha256)}",
    ]
    return "\n".join(lines) + "\n"


def _collection_toml(collection_id: str, title: str, work_ids: list[str]) -> str:
    lines = [
        "schema_version = 1",
        f"id = {_quote(collection_id)}",
        f"title = {_quote(title)}",
        'description = "Developer-reviewed selection discovered from a Lib.ru catalog."',
        "works = [",
    ]
    lines.extend(f"  {_quote(work_id)}," for work_id in work_ids)
    lines.append("]")
    return "\n".join(lines) + "\n"


def register_selection(
    *, selection_path: Path, cache_dir: Path, registry_dir: Path, collection_id: str | None
) -> list[Path]:
    """Writes acquired included works as disabled candidate registry records and a collection."""
    manifest = load_selection(selection_path)
    included = manifest.included()
    if not included:
        raise ValueError("Selection has no works with decision = 'include'")
    if manifest.source_family != "libru":
        raise ValueError(
            f"Selection registration is not implemented for {manifest.source_family!r}"
        )

    works_dir = registry_dir / "works"
    collections_dir = registry_dir / "collections"
    works_dir.mkdir(parents=True, exist_ok=True)
    collections_dir.mkdir(parents=True, exist_ok=True)

    resolved_collection_id = collection_id or _slug(
        f"libru-{manifest.source_url.rstrip('/').rsplit('/', 1)[-1]}"
    )
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", resolved_collection_id):
        raise ValueError(f"Invalid collection id: {resolved_collection_id!r}")
    collection_path = collections_dir / f"{resolved_collection_id}.toml"
    if collection_path.exists():
        raise ValueError(f"Collection already exists: {collection_path}")

    prepared: list[tuple[object, object, Path]] = []
    work_ids: list[str] = []
    for selected_work in included:
        work, version = selection_registry_models(manifest, selected_work)
        artifact = read_source_artifact(cache_dir, work.work_id, version.id)
        target_id = selected_work.registry_work_id or selected_work.id
        target = works_dir / f"{target_id}.toml"
        if target.exists():
            raise ValueError(
                f"Registry work already exists: {target_id}. "
                f"Merge the Lib.ru text version manually into {target}; "
                "registration never overwrites records."
            )
        prepared.append((selected_work, artifact, target))
        work_ids.append(target_id)

    written: list[Path] = []
    for selected_work, artifact, target in prepared:
        target.write_text(_work_toml(manifest, selected_work, artifact), encoding="utf-8")
        written.append(target)

    collection_path.write_text(
        _collection_toml(
            resolved_collection_id,
            f"Lib.ru selection: {manifest.author}",
            work_ids,
        ),
        encoding="utf-8",
    )
    written.append(collection_path)
    return written
