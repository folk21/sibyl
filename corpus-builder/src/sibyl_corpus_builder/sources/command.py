"""CLI adapter for source-ingestion commands.

This module translates argparse values into calls on ``sources.api``. The root CLI only composes
feature command modules and therefore does not need to know about Lib.ru, registry records,
artifact caches, or source preparation details.
"""

import argparse
from pathlib import Path

from .api import (
    acquire_selection,
    discover_to_file,
    fetch_registry_source,
    import_registry_source,
    prepare_registry_sources,
    prepare_selection_sources,
    register_selection,
)

_COMMANDS = {
    "discover",
    "acquire",
    "prepare-selection",
    "register",
    "fetch",
    "import-file",
    "prepare",
}


def _approval_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-unapproved",
        action="store_true",
        help="Allow candidate/review-required sources for local development only",
    )


def register_commands(subparsers) -> None:
    """Registers source-ingestion subcommands on the shared root parser."""
    discover = subparsers.add_parser(
        "discover", help="Discover source works from a supported author/catalog URL"
    )
    discover.add_argument("--url", required=True)
    discover.add_argument("--output", type=Path, required=True)

    acquire = subparsers.add_parser(
        "acquire", help="Acquire all works marked include in a reviewed selection manifest"
    )
    acquire.add_argument("--selection", type=Path, required=True)
    acquire.add_argument("--cache", type=Path, required=True)
    acquire.add_argument("--report", type=Path)

    prepare_selection = subparsers.add_parser(
        "prepare-selection",
        help="Create deterministic prepared input for all included works in a selection",
    )
    prepare_selection.add_argument("--selection", type=Path, required=True)
    prepare_selection.add_argument("--cache", type=Path, required=True)
    prepare_selection.add_argument("--output", type=Path, required=True)

    register = subparsers.add_parser(
        "register", help="Register acquired included works as permanent candidate source records"
    )
    register.add_argument("--selection", type=Path, required=True)
    register.add_argument("--cache", type=Path, required=True)
    register.add_argument("--registry", type=Path, required=True)
    register.add_argument("--collection")

    fetch = subparsers.add_parser(
        "fetch", help="Fetch a registry source into the local artifact cache"
    )
    fetch.add_argument("--registry", type=Path, required=True)
    fetch.add_argument("--work", required=True)
    fetch.add_argument("--version")
    fetch.add_argument("--cache", type=Path, required=True)
    _approval_flag(fetch)

    import_file = subparsers.add_parser(
        "import-file", help="Import a manually reviewed UTF-8 source artifact into the local cache"
    )
    import_file.add_argument("--registry", type=Path, required=True)
    import_file.add_argument("--work", required=True)
    import_file.add_argument("--version")
    import_file.add_argument("--file", type=Path, required=True)
    import_file.add_argument("--cache", type=Path, required=True)
    _approval_flag(import_file)

    prepare = subparsers.add_parser(
        "prepare", help="Create deterministic canonical input from cached registry sources"
    )
    prepare.add_argument("--registry", type=Path, required=True)
    prepare.add_argument("--work", action="append", required=True)
    prepare.add_argument("--cache", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    _approval_flag(prepare)


def dispatch(args) -> bool:
    """Runs one source command and returns whether this feature owned the parsed command."""
    if args.command not in _COMMANDS:
        return False
    if args.command == "discover":
        manifest = discover_to_file(args.url, args.output)
        counts = {decision: 0 for decision in ("include", "review", "exclude")}
        for work in manifest.works:
            counts[work.decision] += 1
        print(
            f"Discovered {len(manifest.works)} works for {manifest.author}: "
            f"{counts['include']} include, {counts['review']} review, {counts['exclude']} exclude"
        )
        print(f"Review selection file: {args.output}")
    elif args.command == "acquire":
        report = acquire_selection(
            selection_path=args.selection, cache_dir=args.cache, report_path=args.report
        )
        report_path = args.report or args.selection.with_name(
            f"{args.selection.stem}-acquire-report.toml"
        )
        print(
            f"Acquisition complete: {len(report.acquired)} acquired, "
            f"{len(report.failed)} failed, {len(report.skipped)} skipped"
        )
        print(f"Report: {report_path}")
        for item in report.failed:
            print(f"FAILED {item.work_id}: {item.error}")
        if report.failed:
            raise SystemExit(2)
    elif args.command == "prepare-selection":
        prepare_selection_sources(
            selection_path=args.selection, cache_dir=args.cache, output_dir=args.output
        )
        print(f"Prepared selected canonical source input in {args.output}")
    elif args.command == "register":
        paths = register_selection(
            selection_path=args.selection,
            cache_dir=args.cache,
            registry_dir=args.registry,
            collection_id=args.collection,
        )
        print(f"Registered {len(paths) - 1} works and 1 collection")
        for path in paths:
            print(path)
    elif args.command == "fetch":
        path = fetch_registry_source(
            registry_dir=args.registry,
            cache_dir=args.cache,
            work_id=args.work,
            version_id=args.version,
            allow_unapproved=args.allow_unapproved,
        )
        print(f"Fetched source artifact: {path}")
    elif args.command == "import-file":
        path = import_registry_source(
            registry_dir=args.registry,
            cache_dir=args.cache,
            work_id=args.work,
            version_id=args.version,
            file_path=args.file,
            allow_unapproved=args.allow_unapproved,
        )
        print(f"Imported source artifact: {path}")
    elif args.command == "prepare":
        prepare_registry_sources(
            registry_dir=args.registry,
            cache_dir=args.cache,
            work_ids=args.work,
            output_dir=args.output,
            allow_unapproved=args.allow_unapproved,
        )
        print(f"Prepared canonical source input in {args.output}")
    return True
