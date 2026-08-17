"""CLI adapter for export -> large LLM -> import/validate curation workflow commands."""

from pathlib import Path

from .api import export_curation_bundle, import_curation, validate_curated_curation

_COMMANDS = {"export-curation-bundle", "import-curation", "validate-curation"}


def register_commands(subparsers) -> None:
    """Registers large-LLM curation subcommands on the shared root parser."""
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

    import_parser = subparsers.add_parser(
        "import-curation",
        help="Validate an LLM curation proposal against canonical text and normalize it",
    )
    import_parser.add_argument("--source", type=Path, required=True)
    import_parser.add_argument("--questions", type=Path, required=True)
    import_parser.add_argument("--input", type=Path, required=True)
    import_parser.add_argument("--output", type=Path, required=True)

    validate_parser = subparsers.add_parser(
        "validate-curation",
        help="Revalidate normalized curated mappings against prepared canonical text",
    )
    validate_parser.add_argument("--source", type=Path, required=True)
    validate_parser.add_argument("--questions", type=Path, required=True)
    validate_parser.add_argument("--curation", type=Path, required=True)


def dispatch(args) -> bool:
    """Runs one curation command and returns whether this feature owned it."""
    if args.command not in _COMMANDS:
        return False
    if args.command == "export-curation-bundle":
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
    return True
