import json
from pathlib import Path

import pytest

from sibyl_corpus_builder.config import load_config
from sibyl_corpus_builder.runtime_model import download_runtime_model


def _config(tmp_path: Path, query_prefix: str = "query: ") -> Path:
    path = tmp_path / "config.toml"
    path.write_text(
        f'''\n[corpus]\nformat_version = 3\nlanguage = "ru"\n\n[passages]\nmin_words = 5\npreferred_words = 10\nmax_words = 40\noverlap_paragraphs = 0\n\n[hints]\nhints_per_passage = 1\nprovider = "passage_text"\n\n[embeddings]\nprovider = "sentence_transformers"\nmodel_id = "intfloat/multilingual-e5-small"\ndimensions = 384\nnormalize = true\npassage_prefix = "passage: "\nquery_prefix = "{query_prefix}"\n'''.strip(),
        encoding="utf-8",
    )
    return path


def test_runtime_model_bundle_is_reproducible_without_network(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    downloaded: list[str] = []

    def downloader(url: str, destination: Path) -> None:
        downloaded.append(url)
        destination.write_bytes(f"fixture:{destination.name}".encode())

    output = download_runtime_model(config, tmp_path / "runtime-model", downloader=downloader)
    manifest = json.loads((output / "model-manifest.json").read_text(encoding="utf-8"))

    assert len(downloaded) == 2
    assert manifest["model_id"] == "intfloat/multilingual-e5-small"
    assert manifest["dimensions"] == 384
    assert manifest["query_prefix"] == "query: "
    assert manifest["pooling"] == "mean"
    assert manifest["max_length"] == 512
    assert set(manifest["sha256"]) == {"model.onnx", "tokenizer.json"}


def test_runtime_model_requires_query_prefix(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path, query_prefix=""))
    with pytest.raises(ValueError, match="query_prefix"):
        download_runtime_model(config, tmp_path / "runtime-model", downloader=lambda _u, _p: None)
