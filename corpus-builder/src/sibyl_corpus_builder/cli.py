import argparse
from pathlib import Path

from .builder import build_corpus
from .config import load_config
from .validation import validate_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sibyl-corpus")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build a development corpus")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--source", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate", help="Validate a corpus database")
    validate.add_argument("--corpus", type=Path, required=True)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "build":
        config = load_config(args.config)
        build_corpus(config, args.source, args.output)
        validate_corpus(args.output / "corpus.db")
        print(f"Built and validated corpus in {args.output}")
    elif args.command == "validate":
        validate_corpus(args.corpus)
        print(f"Corpus is valid: {args.corpus}")


if __name__ == "__main__":
    main()
