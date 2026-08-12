from pathlib import Path

import pytest

from sibyl_corpus_builder import builder
from sibyl_corpus_builder.config import BuilderConfig, EmbeddingConfig, HintConfig, PassageConfig
from sibyl_corpus_builder.models import SemanticHint


class _RecordingProvider:
    def __init__(self, *, dimensions: int, fail_after_calls: int | None = None) -> None:
        self._dimensions = dimensions
        self._fail_after_calls = fail_after_calls
        self.calls = 0
        self.texts: list[str] = []

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_id(self) -> str | None:
        return None

    def embed_many(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        del batch_size
        self.calls += 1
        if self._fail_after_calls is not None and self.calls > self._fail_after_calls:
            raise RuntimeError("simulated interruption")
        self.texts.extend(texts)
        return [[float(index + 1)] * self._dimensions for index, _ in enumerate(texts)]


def _config() -> BuilderConfig:
    return BuilderConfig(
        format_version=3,
        language="en",
        passages=PassageConfig(1, 2, 4, 0),
        hints=HintConfig(provider="passage_text", hints_per_passage=1),
        embeddings=EmbeddingConfig(
            provider="hash",
            dimensions=4,
            normalize=True,
            batch_size=1,
            cache=True,
        ),
    )


def test_embedding_cache_resumes_after_completed_batches(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    hints = [
        SemanticHint(hint_id="h1", passage_id="p1", text="alpha"),
        SemanticHint(hint_id="h2", passage_id="p2", text="beta"),
        SemanticHint(hint_id="h3", passage_id="p3", text="gamma"),
    ]

    first = _RecordingProvider(dimensions=4, fail_after_calls=1)
    monkeypatch.setattr(builder, "_embedding_provider", lambda config: first)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        builder._resolve_embeddings(_config(), hints, tmp_path)

    assert first.texts == ["alpha"]

    second = _RecordingProvider(dimensions=4)
    monkeypatch.setattr(builder, "_embedding_provider", lambda config: second)
    vectors = builder._resolve_embeddings(_config(), hints, tmp_path)

    assert second.texts == ["beta", "gamma"]
    assert set(vectors) == {"h1", "h2", "h3"}
    output = capsys.readouterr().out
    assert "1 cached, 2 to compute" in output


def test_embedding_cache_avoids_loading_provider_when_complete(
    tmp_path: Path, monkeypatch
) -> None:
    hints = [SemanticHint(hint_id="h1", passage_id="p1", text="same text")]
    provider = _RecordingProvider(dimensions=4)
    monkeypatch.setattr(builder, "_embedding_provider", lambda config: provider)
    builder._resolve_embeddings(_config(), hints, tmp_path)

    def fail_if_loaded(config):
        raise AssertionError("provider should not be loaded for a complete cache")

    monkeypatch.setattr(builder, "_embedding_provider", fail_if_loaded)
    vectors = builder._resolve_embeddings(_config(), hints, tmp_path)

    assert vectors["h1"]
