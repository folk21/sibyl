"""Desktop runtime-model bundle support for local query embedding.

This private build subpackage packages the model-side compatibility bridge
between Python corpus generation and the JVM Desktop development runtime.
``specs`` defines explicitly supported model assets and runtime assumptions;
``download`` fetches, hashes, validates, and atomically publishes the ONNX and
tokenizer bundle required to embed user queries locally.

Pipeline position::

    build embedding configuration
        -> explicit download-runtime-model command
        -> pinned ONNX/tokenizer assets + model manifest
        -> Desktop local EmbeddingEngine

Model download is an explicit networked developer action and must never occur
on package import or during default tests. This package does not generate
corpus passage embeddings and does not participate in runtime retrieval beyond
preparing the compatible local model bundle.
"""

from .download import download_runtime_model

__all__ = ["download_runtime_model"]
