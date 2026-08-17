"""Exact canonical-text locator primitives shared by automatic and LLM curation flows."""

import re
from dataclasses import dataclass

_CHAR_LOCATOR = re.compile(r"chars:(\d+):(\d+)")


@dataclass(frozen=True)
class CharacterRange:
    """A half-open character range into one exact canonical text version."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError(f"Invalid character range: {self.start}:{self.end}")

    @property
    def locator(self) -> str:
        """Returns the persisted ``chars:start:end`` representation."""
        return f"chars:{self.start}:{self.end}"

    def extract(self, text: str) -> str:
        """Returns the exact canonical slice and rejects ranges outside the text."""
        if self.end > len(text):
            raise ValueError(
                f"Character range {self.locator} exceeds canonical text length {len(text)}"
            )
        return text[self.start : self.end]


def parse_character_locator(value: object) -> CharacterRange:
    """Parses a persisted ``chars:start:end`` locator into a validated range."""
    locator = str(value)
    match = _CHAR_LOCATOR.fullmatch(locator)
    if match is None:
        raise ValueError(f"Invalid character locator: {locator!r}")
    return CharacterRange(start=int(match.group(1)), end=int(match.group(2)))
