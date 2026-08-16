import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

_ALLOWED_DECISIONS = {"include", "exclude", "review"}


@dataclass(frozen=True)
class SelectionWork:
    """Editable discovery result with an explicit include, exclude, or review decision."""

    id: str
    title: str
    source_url: str
    decision: str
    reason: str
    year: int | None = None
    genres: tuple[str, ...] = ()
    registry_work_id: str | None = None


@dataclass(frozen=True)
class SelectionManifest:
    """Developer-reviewed catalog selection used by later acquisition commands."""

    source_family: str
    source_url: str
    author: str
    language: str
    original_language: str
    category: str
    works: tuple[SelectionWork, ...]

    def included(self) -> tuple[SelectionWork, ...]:
        return tuple(work for work in self.works if work.decision == "include")


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _array(values: tuple[str, ...] | list[str]) -> str:
    return "[" + ", ".join(_quote(value) for value in values) + "]"


def write_selection(manifest: SelectionManifest, path: Path) -> None:
    """Writes an editable deterministic TOML selection manifest."""
    lines = [
        "schema_version = 1",
        f"source_family = {_quote(manifest.source_family)}",
        f"source_url = {_quote(manifest.source_url)}",
        f"author = {_quote(manifest.author)}",
        f"language = {_quote(manifest.language)}",
        f"original_language = {_quote(manifest.original_language)}",
        f"category = {_quote(manifest.category)}",
        "",
        "# Edit decision to include/exclude/review before acquisition.",
        "# registry_work_id is optional; it is used only for permanent registration.",
    ]
    for work in manifest.works:
        lines.extend(
            [
                "",
                "[[works]]",
                f"id = {_quote(work.id)}",
                f"title = {_quote(work.title)}",
                f"source_url = {_quote(work.source_url)}",
                f"decision = {_quote(work.decision)}",
                f"reason = {_quote(work.reason)}",
            ]
        )
        if work.year is not None:
            lines.append(f"year = {work.year}")
        if work.genres:
            lines.append(f"genres = {_array(work.genres)}")
        lines.append(f"registry_work_id = {_quote(work.registry_work_id or '')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_selection(path: Path) -> SelectionManifest:
    """Loads and validates a developer-reviewed catalog selection manifest."""
    if not path.is_file():
        raise ValueError(f"Selection file does not exist: {path}")
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported selection schema_version in {path}")

    works: list[SelectionWork] = []
    seen_ids: set[str] = set()
    for item in raw.get("works", []):
        decision = str(item.get("decision", "review"))
        if decision not in _ALLOWED_DECISIONS:
            raise ValueError(f"Invalid selection decision {decision!r}")
        work_id = str(item["id"])
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", work_id):
            raise ValueError(f"Invalid selection work id: {work_id!r}")
        if work_id in seen_ids:
            raise ValueError(f"Duplicate selection work id: {work_id}")
        seen_ids.add(work_id)
        source_url = str(item["source_url"])
        if urlparse(source_url).scheme not in {"http", "https"}:
            raise ValueError(f"Invalid selection source URL: {source_url!r}")
        registry_work_id = str(item.get("registry_work_id", "")).strip() or None
        if registry_work_id and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", registry_work_id):
            raise ValueError(f"Invalid registry work id: {registry_work_id!r}")
        works.append(
            SelectionWork(
                id=work_id,
                title=str(item["title"]),
                source_url=source_url,
                decision=decision,
                reason=str(item.get("reason", "")),
                year=int(item["year"]) if item.get("year") is not None else None,
                genres=tuple(str(value) for value in item.get("genres", [])),
                registry_work_id=registry_work_id,
            )
        )
    if not works:
        raise ValueError(f"Selection contains no works: {path}")

    return SelectionManifest(
        source_family=str(raw["source_family"]),
        source_url=str(raw["source_url"]),
        author=str(raw["author"]),
        language=str(raw.get("language", "ru")),
        original_language=str(raw.get("original_language", "ru")),
        category=str(raw.get("category", "literature")),
        works=tuple(works),
    )
