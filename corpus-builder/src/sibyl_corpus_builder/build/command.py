"""CLI adapter for automatic corpus build, inspection, validation, and model-bundle commands."""

from pathlib import Path

from .api import (
    build_available_corpus,
    build_corpus,
    download_runtime_model,
    inspect_passages,
    load_config,
    validate_corpus,
)

_COMMANDS = {
    "inspect-passages",
    "build",
    "build-available",
    "download-runtime-model",
    "validate",
}


def register_commands(subparsers) -> None:
    """Registers automatic-build subcommands on the shared root parser."""
    inspect = subparsers.add_parser(
        "inspect-passages", help="Write automatic passage candidates as JSON Lines for review"
    )
    inspect.add_argument("--config", type=Path, required=True)
    inspect.add_argument("--source", type=Path, required=True)
    inspect.add_argument("--output", type=Path, required=True)

    build = subparsers.add_parser("build", help="Build a runtime corpus from prepared source input")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument(
        "--source",
        type=Path,
        action="append",
        required=True,
        help="Prepared canonical source directory; repeat to assemble multiple source sets",
    )
    build.add_argument(
        "--questions",
        type=Path,
        help="Optional guided-question catalog to persist; required when --curation is used",
    )
    build.add_argument(
        "--curation",
        type=Path,
        action="append",
        default=[],
        help="Validated curated metadata to materialize; repeat for multiple curation sets",
    )
    build.add_argument(
        "--translation",
        type=Path,
        action="append",
        default=[],
        help="Validated machine-translation artifact; repeat for multiple translation sets",
    )
    build.add_argument("--output", type=Path, required=True)

    available = subparsers.add_parser(
        "build-available",
        help="Build one runtime corpus from all locally prepared source sets",
    )
    available.add_argument("--config", type=Path, required=True)
    available.add_argument(
        "--source-root",
        type=Path,
        required=True,
        help="Directory whose immediate prepared-source children contain manifest.json",
    )
    available.add_argument(
        "--questions",
        type=Path,
        help="Optional guided-question catalog; required when available curations are used",
    )
    available.add_argument(
        "--curation-root",
        type=Path,
        help="Optional directory containing validated curated *.json metadata",
    )
    available.add_argument(
        "--translation-root",
        type=Path,
        help="Optional directory containing local validated machine-translation *.json files",
    )
    available.add_argument("--output", type=Path, required=True)

    runtime_model = subparsers.add_parser(
        "download-runtime-model",
        help="Download the local ONNX/tokenizer bundle required by Desktop runtime",
    )
    runtime_model.add_argument("--config", type=Path, required=True)
    runtime_model.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate", help="Validate a runtime corpus database")
    validate.add_argument("--corpus", type=Path, required=True)


def dispatch(args) -> bool:
    """Runs one automatic-build command and returns whether this feature owned it."""
    if args.command not in _COMMANDS:
        return False
    if args.command == "inspect-passages":
        inspect_passages(args.config, args.source, args.output)
    elif args.command == "build":
        config = load_config(args.config)
        build_corpus(
            config,
            args.source,
            args.output,
            questions_path=args.questions,
            curation_paths=args.curation,
            translation_paths=args.translation,
        )
        validate_corpus(args.output / "corpus.db")
        print(f"Built and validated corpus in {args.output}")
    elif args.command == "build-available":
        config = load_config(args.config)
        build_available_corpus(
            config,
            args.source_root,
            args.output,
            questions_path=args.questions,
            curation_root=args.curation_root,
            translation_root=args.translation_root,
        )
        validate_corpus(args.output / "corpus.db")
        print(f"Built and validated corpus from available local sources in {args.output}")
    elif args.command == "download-runtime-model":
        config = load_config(args.config)
        path = download_runtime_model(config, args.output)
        print(f"Runtime model bundle is ready: {path}")
    elif args.command == "validate":
        validate_corpus(args.corpus)
        print(f"Corpus is valid: {args.corpus}")
    return True
