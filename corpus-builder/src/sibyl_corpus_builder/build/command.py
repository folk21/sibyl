"""CLI adapter for automatic corpus build, inspection, validation, and model-bundle commands."""

from pathlib import Path

from .api import (
    build_corpus,
    download_runtime_model,
    inspect_passages,
    load_config,
    validate_corpus,
)

_COMMANDS = {"inspect-passages", "build", "download-runtime-model", "validate"}


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
    build.add_argument("--source", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)

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
    return True
