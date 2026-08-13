package io.github.folk21.sibyl.desktop.runtime

import kotlin.test.Test
import kotlin.test.assertFailsWith

class RuntimeManifestsTest {
    @Test
    fun rejectsCorpusWithoutQueryPrefix() {
        val corpus = CorpusManifest(
            formatVersion = 3,
            embedding = CorpusEmbeddingManifest(
                provider = "sentence_transformers",
                modelId = "intfloat/multilingual-e5-small",
                dimensions = 384,
                normalize = true,
                passagePrefix = "passage: ",
                queryPrefix = "",
            ),
            artifacts = CorpusArtifactsManifest("corpus.db", "vectors.json"),
            counts = CorpusCountsManifest(1, 1, 1),
        )
        val model = RuntimeModelManifest(
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

        assertFailsWith<IllegalArgumentException> {
            validateRuntimeCompatibility(corpus, model)
        }
    }
}
