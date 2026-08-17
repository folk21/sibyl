"""Cross-source document-format parsers used during canonicalization.

This package contains parsers for transport/document formats that may appear in
more than one source family. A format parser converts a raw representation into
text blocks suitable for source-specific canonicalization while preserving the
literary wording represented by the document.

FB2 support currently lives here because FB2 is a document format, not a
Lib.ru-specific concept. Source adapters decide when a format parser should be
used and remain responsible for source provenance, fallback order, and any
site-specific wrappers around the document.

Nothing in this package performs network access, source selection, passage
splitting, embedding generation, or corpus publication.
"""
