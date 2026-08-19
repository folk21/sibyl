"""Discovery of locally available prepared sources and compatible curation inputs.

This module supports the convenience build that assembles one runtime corpus from all prepared
canonical source sets currently present under a local work root. It discovers only prepared
manifests and curated metadata files; source acquisition, preparation, and curation validation
remain owned by their existing features.
"""

from pathlib import Path

from sibyl_corpus_core.models import SourceDocument

from ...curation import curation_source_keys


def discover_prepared_source_dirs(source_root: Path) -> tuple[Path, ...]:
    """Finds immediate prepared source-set directories containing ``manifest.json``."""
    if not source_root.is_dir():
        raise ValueError(f"Prepared source root does not exist: {source_root}")
    source_dirs = tuple(
        sorted(
            (
                child
                for child in source_root.iterdir()
                if child.is_dir() and (child / "manifest.json").is_file()
            ),
            key=lambda path: path.name,
        )
    )
    if not source_dirs:
        raise ValueError(f"No prepared source sets found under: {source_root}")
    return source_dirs


def discover_curation_paths(curation_root: Path | None) -> tuple[Path, ...]:
    """Finds deterministic curated JSON inputs from the configured Git-tracked directory."""
    if curation_root is None:
        return ()
    if not curation_root.is_dir():
        raise ValueError(f"Curation root does not exist: {curation_root}")
    return tuple(sorted(curation_root.glob("*.json"), key=lambda path: path.name))


def select_available_curations(
    *,
    documents: list[SourceDocument],
    curation_paths: tuple[Path, ...],
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Selects curations fully backed by available texts and rejects partial availability.

    A curation that references no locally available text versions is skipped because the matching
    author/source set has not been prepared on this workstation. A curation with only some of its
    required text versions available is rejected, because silently publishing a partial curated
    set would make corpus contents depend on accidental local state.
    """
    available = {(document.source_id, document.text_version_id) for document in documents}
    selected: list[Path] = []
    skipped: list[Path] = []
    for path in curation_paths:
        required = curation_source_keys(path)
        present = required.intersection(available)
        if not present:
            skipped.append(path)
            continue
        missing = required - available
        if missing:
            formatted = sorted(f"{work_id}/{version_id}" for work_id, version_id in missing)
            raise ValueError(
                f"Curation {path} is only partially available; missing prepared text versions: "
                f"{formatted}"
            )
        selected.append(path)
    return tuple(selected), tuple(skipped)
