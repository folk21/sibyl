"""CLI adapter for explicit curated-passage machine-translation preparation commands."""

from pathlib import Path

from .api import export_translation_bundle, import_translation, validate_translation

_COMMANDS = {
    "export-translation-bundle",
    "import-translation",
    "validate-translation",
}


def register_commands(subparsers) -> None:
    """Registers build-time machine-translation commands on the shared root parser."""
    export_parser = subparsers.add_parser(
        "export-translation-bundle",
        help="Export validated curated source passages for external LLM translation",
    )
    export_parser.add_argument("--source", type=Path, required=True)
    export_parser.add_argument("--questions", type=Path, required=True)
    export_parser.add_argument("--curation", type=Path, required=True)
    export_parser.add_argument("--target-language", required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument(
        "--allow-unapproved",
        action="store_true",
        help=(
            "Allow external translation export only after separately confirming "
            "source upload rights"
        ),
    )

    import_parser = subparsers.add_parser(
        "import-translation",
        help="Validate a complete external LLM translation proposal and store it locally",
    )
    import_parser.add_argument("--source", type=Path, required=True)
    import_parser.add_argument("--questions", type=Path, required=True)
    import_parser.add_argument("--curation", type=Path, required=True)
    import_parser.add_argument("--target-language", required=True)
    import_parser.add_argument("--input", type=Path, required=True)
    import_parser.add_argument("--output", type=Path, required=True)

    validate_parser = subparsers.add_parser(
        "validate-translation",
        help="Revalidate stored generated translations against current curated source passages",
    )
    validate_parser.add_argument("--source", type=Path, required=True)
    validate_parser.add_argument("--questions", type=Path, required=True)
    validate_parser.add_argument("--curation", type=Path, required=True)
    validate_parser.add_argument("--translation", type=Path, required=True)


def dispatch(args) -> bool:
    """Runs one translation command and returns whether this feature owned it."""
    if args.command not in _COMMANDS:
        return False
    if args.command == "export-translation-bundle":
        output = export_translation_bundle(
            source_dir=args.source,
            questions_path=args.questions,
            curation_path=args.curation,
            target_language=args.target_language,
            output_path=args.output,
            allow_unapproved=args.allow_unapproved,
        )
        print(f"Exported local LLM translation bundle: {output}")
    elif args.command == "import-translation":
        output = import_translation(
            source_dir=args.source,
            questions_path=args.questions,
            curation_path=args.curation,
            target_language=args.target_language,
            input_path=args.input,
            output_path=args.output,
        )
        print(f"Imported and validated machine translations: {output}")
    elif args.command == "validate-translation":
        validate_translation(
            source_dir=args.source,
            questions_path=args.questions,
            curation_path=args.curation,
            translation_path=args.translation,
        )
        print(f"Machine translations are valid: {args.translation}")
    return True
