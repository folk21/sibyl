"""Build-time corpus tooling for Sibyl.

This package is the side-effect-free composition layer for the ``sources``,
``build``, and ``curation`` features. Those features turn external literary
sources into prepared canonical text, runtime corpus artifacts, or validated
curation metadata. Runtime question answering belongs to the application, and
package import must never trigger downloads, model loading, or data mutation."""

__version__ = "0.6.0"
