"""Project Gutenberg acquisition and canonicalization adapter.

The Project Gutenberg adapter handles the source-specific part of turning a
reviewed Gutenberg work version into canonical text. ``fetch`` locates a
preferred UTF-8 plain-text artifact from a work page when a download URI is not
already pinned, and ``normalize`` removes the recognized Gutenberg START/END
transport wrapper without rewriting the literary body.

Pipeline position::

    reviewed Gutenberg source version
        -> fetch preferred text artifact
        -> remove Gutenberg transport wrapper
        -> generic source artifact cache
        -> prepared canonical source

Network access is explicit and occurs only when the acquisition workflow calls
the fetch adapter. Importing this package performs no download. Rights,
registry approval, caching, and publication remain responsibilities of the
surrounding ``sources`` feature rather than this adapter.
"""
