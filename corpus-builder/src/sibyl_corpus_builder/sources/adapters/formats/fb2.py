"""FB2-to-canonical-text conversion shared by source adapters.

FB2 is treated as a transport/document format rather than a source family. A source adapter
may delegate here after acquisition when its downloaded candidate is FB2 or zipped FB2.
The conversion keeps only the primary literary body and preserves paragraph wording.
"""

import xml.etree.ElementTree as ET
from io import BytesIO
from zipfile import BadZipFile, ZipFile


def _fb2_payload(raw: bytes) -> bytes:
    if not raw.startswith(b"PK"):
        return raw
    try:
        with ZipFile(BytesIO(raw)) as archive:
            candidates = sorted(
                name
                for name in archive.namelist()
                if name.lower().endswith((".fb2", ".xml")) and not name.endswith("/")
            )
            if not candidates:
                raise ValueError("FB2 ZIP archive contains no .fb2 or .xml document")
            return archive.read(candidates[0])
    except BadZipFile as error:
        raise ValueError("Invalid FB2 ZIP archive") from error


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _inline_text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def canonicalize_fb2(raw: bytes) -> str:
    """Extracts literary blocks from the primary FB2 body without editorial notes."""
    payload = _fb2_payload(raw)
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError("Invalid FB2 XML document") from error

    bodies = [element for element in root.iter() if _local_name(element.tag) == "body"]
    primary = next(
        (
            body
            for body in bodies
            if body.attrib.get("name", "").casefold() not in {"notes", "comments"}
        ),
        None,
    )
    if primary is None:
        raise ValueError("FB2 document contains no primary body")

    blocks: list[str] = []
    for element in primary.iter():
        name = _local_name(element.tag)
        if name not in {"p", "subtitle", "v", "text-author"}:
            continue
        text = _inline_text(element)
        if text:
            blocks.append(text)
    if not blocks:
        raise ValueError("FB2 primary body contains no text blocks")
    return "\n\n".join(blocks)
