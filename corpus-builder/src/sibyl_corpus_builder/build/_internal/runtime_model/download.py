"""Explicit networked download of a runtime model bundle for Desktop local inference.

Pipeline position:

    automatic-build embedding config -> THIS MODULE -> local ONNX/tokenizer bundle
                                              -> Desktop runtime compatibility checks

This module is invoked only by an explicit CLI command; importing corpus-builder has no network
or model side effects.
"""

import json
import urllib.request
from pathlib import Path
from typing import Callable

from sibyl_corpus_core.atomic import staging_directory
from sibyl_corpus_core.hashing import sha256_file

from ...config import BuilderConfig
from .specs import SUPPORTED_MODELS


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


def download_runtime_model(
    config: BuilderConfig,
    output_dir: Path,
    downloader: Callable[[str, Path], None] = _download,
) -> Path:
    """Downloads, hashes, manifests, and atomically publishes the Desktop model bundle."""
    model_id = config.embeddings.model_id
    if model_id is None:
        raise ValueError("embeddings.model_id is required for a runtime model bundle")
    spec = SUPPORTED_MODELS.get(model_id)
    if spec is None:
        raise ValueError(f"No runtime model bundle recipe is defined for {model_id}")
    if not config.embeddings.query_prefix:
        raise ValueError("embeddings.query_prefix is required for runtime query embedding")

    output_dir = output_dir.resolve()
    with staging_directory(output_dir) as staging:
        hashes: dict[str, str] = {}
        for asset in spec.assets:
            path = staging / asset.name
            print(f"Fetching runtime model asset: {asset.name}", flush=True)
            downloader(asset.url, path)
            hashes[asset.name] = sha256_file(path)

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
    return output_dir
