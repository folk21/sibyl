"""Pinned recipes for Desktop runtime embedding bundles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeModelAsset:
    """One file required by a local Desktop embedding model bundle."""

    name: str
    url: str


@dataclass(frozen=True)
class RuntimeModelSpec:
    """Runtime files/assumptions compatible with one build-time embedding model."""

    model_id: str
    model_file: str
    tokenizer_file: str
    max_length: int
    pooling: str
    assets: tuple[RuntimeModelAsset, ...]


SUPPORTED_MODELS = {
    "intfloat/multilingual-e5-small": RuntimeModelSpec(
        model_id="intfloat/multilingual-e5-small",
        model_file="model.onnx",
        tokenizer_file="tokenizer.json",
        max_length=512,
        pooling="mean",
        assets=(
            RuntimeModelAsset(
                name="model.onnx",
                url=(
                    "https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx/"
                    "model_O4.onnx?download=true"
                ),
            ),
            RuntimeModelAsset(
                name="tokenizer.json",
                url=(
                    "https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx/"
                    "tokenizer.json?download=true"
                ),
            ),
        ),
    )
}
