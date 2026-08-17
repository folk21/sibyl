"""Build-time corpus tooling for Sibyl.

This package is the Python application layer used to prepare and publish local
corpus data. Its root is intentionally small: :mod:`sibyl_corpus_builder.cli`
acts as the composition root, while the actual workflows are grouped into the
``sources``, ``build``, and ``curation`` feature packages.

Pipeline position::

    external literary sources
        -> sources
        -> prepared canonical text
        -> build / curation
        -> validated corpus artifacts or curated metadata

Importing this package must remain side-effect free. It must not download
sources or models, contact external services, or mutate generated data merely
because the package was imported. Runtime question answering also does not
belong here; that remains in the mobile/Desktop application.
"""

__version__ = "0.6.0"
