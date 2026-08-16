package io.github.folk21.sibyl.desktop.runtime

import ai.djl.huggingface.tokenizers.HuggingFaceTokenizer
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import io.github.folk21.sibyl.retrieval.EmbeddingEngine
import java.nio.LongBuffer
import java.nio.file.Files
import java.nio.file.Path
import kotlin.math.sqrt

/** Encodes runtime questions with the local E5 ONNX model and tokenizer. */
class OnnxE5EmbeddingEngine(
    modelPath: Path,
    tokenizerPath: Path,
    private val dimensions: Int,
    private val queryPrefix: String,
    private val maxLength: Int,
    private val normalize: Boolean,
) : EmbeddingEngine, AutoCloseable {
    private val environment = OrtEnvironment.getEnvironment()
    private val session: OrtSession
    private val tokenizer: HuggingFaceTokenizer

    init {
        require(Files.isRegularFile(modelPath)) { "ONNX model not found: $modelPath" }
        require(Files.isRegularFile(tokenizerPath)) { "Tokenizer not found: $tokenizerPath" }
        session = environment.createSession(modelPath.toString(), OrtSession.SessionOptions())
        tokenizer = HuggingFaceTokenizer.builder()
            .optTokenizerPath(tokenizerPath)
            .optTruncation(true)
            .optMaxLength(maxLength)
            .build()
    }

    /** Tokenizes a query, runs ONNX inference, mean-pools active tokens, and normalizes the result. */
    override suspend fun embed(text: String): FloatArray {
        val encoding = tokenizer.encode(queryPrefix + text)
        val ids = encoding.ids
        val attention = encoding.attentionMask
        require(ids.isNotEmpty()) { "Tokenizer returned an empty sequence" }
        require(ids.size == attention.size) { "Tokenizer ids and attention mask lengths differ" }

        val shape = longArrayOf(1, ids.size.toLong())
        val inputs = linkedMapOf<String, OnnxTensor>()
        inputs["input_ids"] = OnnxTensor.createTensor(environment, LongBuffer.wrap(ids), shape)
        inputs["attention_mask"] = OnnxTensor.createTensor(
            environment,
            LongBuffer.wrap(attention),
            shape,
        )
        if ("token_type_ids" in session.inputNames) {
            inputs["token_type_ids"] = OnnxTensor.createTensor(
                environment,
                LongBuffer.wrap(LongArray(ids.size)),
                shape,
            )
        }

        try {
            session.run(inputs).use { result ->
                @Suppress("UNCHECKED_CAST")
                val output = result[0].value as Array<Array<FloatArray>>
                val tokens = output[0]
                require(tokens.isNotEmpty()) { "ONNX model returned no token embeddings" }
                require(tokens[0].size == dimensions) {
                    "ONNX output has ${tokens[0].size} dimensions; expected $dimensions"
                }
                val pooled = FloatArray(dimensions)
                var tokenCount = 0
                for (tokenIndex in tokens.indices) {
                    if (attention[tokenIndex] == 0L) continue
                    tokenCount += 1
                    for (dimension in 0 until dimensions) {
                        pooled[dimension] += tokens[tokenIndex][dimension]
                    }
                }
                require(tokenCount > 0) { "Attention mask contains no active tokens" }
                for (dimension in pooled.indices) {
                    pooled[dimension] /= tokenCount.toFloat()
                }
                if (normalize) normalizeInPlace(pooled)
                return pooled
            }
        } finally {
            inputs.values.forEach(OnnxTensor::close)
        }
    }

    private fun normalizeInPlace(vector: FloatArray) {
        var sum = 0.0
        for (value in vector) sum += value * value
        val norm = sqrt(sum)
        require(norm > 0.0) { "Embedding has a zero norm" }
        for (index in vector.indices) vector[index] = (vector[index] / norm).toFloat()
    }

    override fun close() {
        tokenizer.close()
        session.close()
    }
}
