import hashlib
from typing import Protocol

from .models import PassageCandidate, SemanticHint


class HintGenerator(Protocol):
    def generate(self, passage: PassageCandidate, count: int) -> list[SemanticHint]: ...


class DeterministicHintGenerator:
    """Development-only hint generator that keeps repository tests model-free."""

    def generate(self, passage: PassageCandidate, count: int) -> list[SemanticHint]:
        compact = " ".join(passage.text.split())
        base = compact[:280]
        hints: list[SemanticHint] = []
        for index in range(count):
            text = base if index == 0 else f"A related literary situation: {base}"
            digest = hashlib.sha256(
                f"{passage.passage_id}:{index}:{text}".encode("utf-8")
            ).hexdigest()[:20]
            hints.append(
                SemanticHint(
                    hint_id=f"h_{digest}", passage_id=passage.passage_id, text=text
                )
            )
        return hints


class PassageTextHintGenerator:
    """Indexes the exact passage text until semantic-hint generation is introduced."""

    def generate(self, passage: PassageCandidate, count: int) -> list[SemanticHint]:
        if count != 1:
            raise ValueError("passage_text hint provider requires hints_per_passage = 1")
        digest = hashlib.sha256(
            f"{passage.passage_id}:passage_text".encode("utf-8")
        ).hexdigest()[:20]
        return [
            SemanticHint(
                hint_id=f"h_{digest}",
                passage_id=passage.passage_id,
                text=passage.text,
            )
        ]
