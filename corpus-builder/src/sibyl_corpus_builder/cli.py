import argparse
import json
from pathlib import Path

from .builder import build_corpus
from .config import load_config
from .curation import export_curation_bundle, import_curation, validate_curated_curation
from .discovery import discover_to_file
from .preparation import (
    acquire_selection,
    fetch_registry_source,
    import_registry_source,
    prepare_registry_sources,
    prepare_selection_sources,
)
from .registration import register_selection
from .runtime_model import download_runtime_model
from .source_loader import load_sources
from .splitter import split_document
from .validation import validate_corpus


def _approval_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-unapproved",
        action="store_true",
        help="Allow candidate/review-required sources for local development only",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit CLI for discovery, preparation, validation, and publication."""
    parser = argparse.ArgumentParser(prog="sibyl-corpus")
    subparsers = parser.add_subparsers(dest="command", required=True)

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
        help="Create deterministic builder input for all included works in a selection",
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
        "prepare", help="Create deterministic canonical builder input from cached registry sources"
    )
    prepare.add_argument("--registry", type=Path, required=True)
    prepare.add_argument("--work", action="append", required=True)
    prepare.add_argument("--cache", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    _approval_flag(prepare)

    inspect = subparsers.add_parser(
        "inspect-passages", help="Write extracted passage candidates as JSON Lines for review"
    )
    inspect.add_argument("--config", type=Path, required=True)
    inspect.add_argument("--source", type=Path, required=True)
    inspect.add_argument("--output", type=Path, required=True)

    export_curation = subparsers.add_parser(
        "export-curation-bundle",
        help="Export prepared canonical texts and guided questions for external LLM curation",
    )
    export_curation.add_argument("--source", type=Path, required=True)
    export_curation.add_argument("--questions", type=Path, required=True)
    export_curation.add_argument("--output", type=Path, required=True)
    export_curation.add_argument(
        "--work", action="append", help="Optional prepared work ID to include; repeat as needed"
    )
    export_curation.add_argument(
        "--allow-unapproved",
        action="store_true",
        help=(
            "Allow source versions without approved rights metadata; confirm external-service "
            "upload rights separately"
        ),
    )

    import_curation_parser = subparsers.add_parser(
        "import-curation",
        help="Validate an LLM curation proposal against canonical text and normalize it",
    )
    import_curation_parser.add_argument("--source", type=Path, required=True)
    import_curation_parser.add_argument("--questions", type=Path, required=True)
    import_curation_parser.add_argument("--input", type=Path, required=True)
    import_curation_parser.add_argument("--output", type=Path, required=True)

    validate_curation_parser = subparsers.add_parser(
        "validate-curation",
        help="Revalidate normalized curated mappings against prepared canonical text",
    )
    validate_curation_parser.add_argument("--source", type=Path, required=True)
    validate_curation_parser.add_argument("--questions", type=Path, required=True)
    validate_curation_parser.add_argument("--curation", type=Path, required=True)

    build = subparsers.add_parser("build", help="Build a corpus from prepared source input")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--source", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)

    runtime_model = subparsers.add_parser(
        "download-runtime-model",
        help="Download the local ONNX/tokenizer bundle required by Desktop runtime",
    )
    runtime_model.add_argument("--config", type=Path, required=True)
    runtime_model.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate", help="Validate a corpus database")
    validate.add_argument("--corpus", type=Path, required=True)

    return parser


def _inspect_passages(config_path: Path, source_dir: Path, output: Path) -> None:
    """Writes exact extracted passages as JSONL for developer review before publication."""
    config = load_config(config_path)
    records: list[dict[str, object]] = []
    for document in load_sources(source_dir):
        for passage in split_document(document, config.passages):
            records.append(
                {
                    "passage_id": passage.passage_id,
                    "work_id": passage.source_id,
                    "text_version_id": passage.text_version_id,
                    "ordinal": passage.ordinal,
                    "source_locator": passage.source_locator,
                    "word_count": passage.word_count,
                    "text": passage.text,
                }
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} passage candidates to {output}")


def main() -> None:
    """Dispatches one explicit corpus-builder command without import-time side effects."""
    args = build_parser().parse_args()
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
    elif args.command == "inspect-passages":
        _inspect_passages(args.config, args.source, args.output)
    elif args.command == "export-curation-bundle":
        output = export_curation_bundle(
            source_dir=args.source,
            questions_path=args.questions,
            output_path=args.output,
            work_ids=args.work,
            allow_unapproved=args.allow_unapproved,
        )
        print(f"Exported local LLM curation bundle: {output}")
    elif args.command == "import-curation":
        output = import_curation(
            source_dir=args.source,
            questions_path=args.questions,
            input_path=args.input,
            output_path=args.output,
        )
        print(f"Imported and validated curated mappings: {output}")
    elif args.command == "validate-curation":
        validate_curated_curation(
            source_dir=args.source,
            questions_path=args.questions,
            curation_path=args.curation,
        )
        print(f"Curated mappings are valid: {args.curation}")
    elif args.command == "build":
        config = load_config(args.config)
        build_corpus(config, args.source, args.output)
        validate_corpus(args.output / "corpus.db")
        print(f"Built and validated corpus in {args.output}")
    elif args.command == "download-runtime-model":
        config = load_config(args.config)
        path = download_runtime_model(config, args.output)
        print(f"Runtime model bundle is ready: {path}")
    elif args.command == "validate":
        validate_corpus(args.corpus)
        print(f"Corpus is valid: {args.corpus}")


if __name__ == "__main__":
    main()
