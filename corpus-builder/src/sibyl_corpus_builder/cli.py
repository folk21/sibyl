"""Thin command-line composition root for Sibyl corpus tooling.

The CLI is intentionally the only top-level orchestration entry point in ``sibyl_corpus_builder``.
It does not implement source parsing, passage splitting, embedding logic, or LLM curation. Instead
it composes three feature command adapters:

    sources  -> external text to prepared canonical sources
    build    -> prepared sources plus optional validated curation to runtime corpus artifacts
    curation -> prepared sources through large-LLM selection to verified curated metadata

For the end-to-end operational sequence, start with ``docs/WORKFLOW.md``. For implementation
ownership and package boundaries, see ``corpus-builder/IMPLEMENTATION.md``.
"""

import argparse

from .build import command as build_command
from .curation import command as curation_command
from .sources import command as sources_command

_COMMAND_MODULES = (sources_command, build_command, curation_command)


def build_parser() -> argparse.ArgumentParser:
    """Builds the root parser by composing feature-owned command surfaces."""
    parser = argparse.ArgumentParser(prog="sibyl-corpus")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command_module in _COMMAND_MODULES:
        command_module.register_commands(subparsers)
    return parser


def main() -> None:
    """Parses one explicit command and dispatches it to the owning feature."""
    args = build_parser().parse_args()
    for command_module in _COMMAND_MODULES:
        if command_module.dispatch(args):
            return
    raise AssertionError(f"No feature owns parsed command: {args.command}")


if __name__ == "__main__":
    main()
