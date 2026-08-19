package io.github.folk21.sibyl.desktop.runtime

import kotlin.test.Test
import kotlin.test.assertFailsWith

/** Verifies v3/v4 corpus migration behavior and embedding compatibility checks used before Desktop startup. */
class RuntimeManifestsTest {
    @Test
    fun `accepts format three and four during migration`() {
        validateRuntimeCompatibility(corpus(formatVersion = 3), model())
        validateRuntimeCompatibility(corpus(formatVersion = 4), model())
    }

    @Test
    fun `rejects unsupported newer corpus format`() {
        assertFailsWith<IllegalArgumentException> {
            validateRuntimeCompatibility(corpus(formatVersion = 5), model())
        }
    }

    @Test
    fun rejectsCorpusWithoutQueryPrefix() {
        val corpus = corpus(formatVersion = 4).copy(
            embedding = corpus(formatVersion = 4).embedding.copy(queryPrefix = ""),
        )

        assertFailsWith<IllegalArgumentException> {
            validateRuntimeCompatibility(corpus, model())
        }
    }

    private fun corpus(formatVersion: Int) = CorpusManifest(
        formatVersion = formatVersion,
        embedding = CorpusEmbeddingManifest(
            provider = "sentence_transformers",
            modelId = "intfloat/multilingual-e5-small",
            dimensions = 384,
            normalize = true,
            passagePrefix = "passage: ",
            queryPrefix = "query: ",
        ),
        artifacts = CorpusArtifactsManifest("corpus.db", "vectors.json"),
        counts = CorpusCountsManifest(1, 1, 1),
    )

    private fun model() = RuntimeModelManifest(
        schemaVersion = 1,
        modelId = "intfloat/multilingual-e5-small",
        modelFile = "model.onnx",
        tokenizerFile = "tokenizer.json",
        dimensions = 384,
        normalize = true,
        pooling = "mean",
        queryPrefix = "query: ",
        maxLength = 512,
    )
}
