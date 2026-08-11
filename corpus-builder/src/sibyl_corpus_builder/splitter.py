import hashlib
import re

from .config import PassageConfig
from .models import PassageCandidate, SourceDocument

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n+")


def word_count(text: str) -> int:
    return len(text.split())


def split_document(document: SourceDocument, config: PassageConfig) -> list[PassageCandidate]:
    paragraphs = [p.strip() for p in _PARAGRAPH_BREAK.split(document.text) if p.strip()]
    results: list[PassageCandidate] = []
    index = 0
    ordinal = 0

    while index < len(paragraphs):
        selected: list[str] = []
        count = 0
        cursor = index

        while cursor < len(paragraphs):
            next_paragraph = paragraphs[cursor]
            next_count = word_count(next_paragraph)
            if selected and count + next_count > config.max_words:
                break
            selected.append(next_paragraph)
            count += next_count
            cursor += 1
            if count >= config.preferred_words:
                break

        text = "\n\n".join(selected)
        if count >= config.min_words:
            digest = hashlib.sha256(
                f"{document.source_id}:{ordinal}:{text}".encode("utf-8")
            ).hexdigest()[:20]
            results.append(
                PassageCandidate(
                    passage_id=f"p_{digest}",
                    source_id=document.source_id,
                    text_version_id=document.text_version_id,
                    ordinal=ordinal,
                    text=text,
                    word_count=count,
                )
            )
            ordinal += 1

        if cursor <= index:
            cursor = index + 1
        index = max(index + 1, cursor - config.overlap_paragraphs)

    return results
