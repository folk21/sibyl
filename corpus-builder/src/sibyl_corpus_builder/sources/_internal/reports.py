"""Deterministic human-readable reports for batch source acquisition."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AcquisitionItem:
    """Outcome and artifact metadata for one selected work in an acquisition batch."""

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
    """Groups acquired, failed, and skipped work outcomes for one reviewed selection."""

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
    """Persists batch outcomes so failures can be reviewed/retried without losing successes."""
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
