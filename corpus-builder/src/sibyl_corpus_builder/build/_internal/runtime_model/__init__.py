"""Private support for the Desktop query-embedding model bundle.

This package turns explicit build embedding configuration into a pinned local
ONNX/tokenizer bundle and manifest for Desktop compatibility checks. Download
is an explicit developer action; importing the package performs no network
work, and corpus passage embeddings are produced elsewhere in the build feature."""

from .download import download_runtime_model

__all__ = ["download_runtime_model"]
