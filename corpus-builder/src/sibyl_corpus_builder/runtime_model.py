from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import BuilderConfig


@dataclass(frozen=True)
class RuntimeModelAsset:
    name: str
    url: str


@dataclass(frozen=True)
class RuntimeModelSpec:
    model_id: str
    model_file: str
    tokenizer_file: str
    max_length: int
    pooling: str
    assets: tuple[RuntimeModelAsset, ...]


_SUPPORTED_MODELS = {
    "intfloat/multilingual-e5-small": RuntimeModelSpec(
        model_id="intfloat/multilingual-e5-small",
        model_file="model.onnx",
        tokenizer_file="tokenizer.json",
        max_length=512,
        pooling="mean",
        assets=(
            RuntimeModelAsset(
                name="model.onnx",
                url="https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx/model_O4.onnx?download=true",
            ),
            RuntimeModelAsset(
                name="tokenizer.json",
                url="https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/onnx/tokenizer.json?download=true",
            ),
        ),
    )
}


def _download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url) as response, destination.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0"))
        written = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            written += len(chunk)
            if total:
                percent = written * 100 / total
                print(
                    f"\rDownloading {destination.name}: {written / 1024 / 1024:.1f}/"
                    f"{total / 1024 / 1024:.1f} MiB ({percent:5.1f}%)",
                    end="" if written < total else "\n",
                    flush=True,
                )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_runtime_model(
    config: BuilderConfig,
    output_dir: Path,
    downloader: Callable[[str, Path], None] = _download,
) -> Path:
    model_id = config.embeddings.model_id
    if model_id is None:
        raise ValueError("embeddings.model_id is required for a runtime model bundle")
    spec = _SUPPORTED_MODELS.get(model_id)
    if spec is None:
        raise ValueError(f"No runtime model bundle recipe is defined for {model_id}")
    if not config.embeddings.query_prefix:
        raise ValueError("embeddings.query_prefix is required for runtime query embedding")

    output_dir = output_dir.resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = output_dir.with_name(f".{output_dir.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        hashes: dict[str, str] = {}
        for asset in spec.assets:
            path = staging / asset.name
            print(f"Fetching runtime model asset: {asset.name}", flush=True)
            downloader(asset.url, path)
            hashes[asset.name] = _sha256(path)

        manifest = {
            "schema_version": 1,
            "model_id": spec.model_id,
            "model_file": spec.model_file,
            "tokenizer_file": spec.tokenizer_file,
            "dimensions": config.embeddings.dimensions,
            "normalize": config.embeddings.normalize,
            "pooling": spec.pooling,
            "query_prefix": config.embeddings.query_prefix,
            "max_length": spec.max_length,
            "sha256": hashes,
        }
        (staging / "model-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if output_dir.exists():
            shutil.rmtree(output_dir)
        staging.rename(output_dir)
        return output_dir
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
