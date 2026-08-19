"""Build-time corpus tooling for Sibyl.

This side-effect-free composition layer exposes the ``sources``, ``build``,
``curation``, and ``translation`` features. They produce prepared canonical
text, runtime corpus artifacts, validated curation metadata, or locally
validated machine translations. Runtime question answering belongs to the
application, and package import must never trigger downloads, model loading,
or data mutation.
"""

__version__ = "0.7.0"
