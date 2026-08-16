package io.github.folk21.sibyl.desktop.runtime

import java.nio.file.Files
import java.nio.file.Path
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

private val runtimeJson = Json { ignoreUnknownKeys = true }

/** Embedding compatibility metadata persisted with a published corpus. */
@Serializable
data class CorpusEmbeddingManifest(
    val provider: String,
    @SerialName("model_id") val modelId: String? = null,
    val dimensions: Int,
    val normalize: Boolean,
    @SerialName("passage_prefix") val passagePrefix: String = "",
    @SerialName("query_prefix") val queryPrefix: String = "",
)

/** Relative filenames of runtime corpus artifacts. */
@Serializable
data class CorpusArtifactsManifest(
    val corpus: String,
    val vectors: String,
)

/** Lightweight corpus counts used for diagnostics and the Desktop runtime label. */
@Serializable
data class CorpusCountsManifest(
    val works: Int,
    val passages: Int,
    val hints: Int,
)

/**
 * Minimal subset of the published corpus manifest required by the Desktop reader.
 *
 * Keeping this reader model narrow lets Desktop ignore builder-only metadata while still validating every field that
 * affects embedding compatibility or artifact location.
 */
@Serializable
data class CorpusManifest(
    @SerialName("format_version") val formatVersion: Int,
    val embedding: CorpusEmbeddingManifest,
    val artifacts: CorpusArtifactsManifest,
    val counts: CorpusCountsManifest,
)

/**
 * Runtime contract for a downloaded local ONNX model/tokenizer bundle.
 *
 * These fields describe the inference behavior that must match corpus generation; the model files themselves remain
 * generated local data and are not committed with application source.
 */
@Serializable
data class RuntimeModelManifest(
    @SerialName("schema_version") val schemaVersion: Int,
    @SerialName("model_id") val modelId: String,
    @SerialName("model_file") val modelFile: String,
    @SerialName("tokenizer_file") val tokenizerFile: String,
    val dimensions: Int,
    val normalize: Boolean,
    val pooling: String,
    @SerialName("query_prefix") val queryPrefix: String,
    @SerialName("max_length") val maxLength: Int,
)

/** Loads the published corpus manifest from a runtime corpus directory. */
fun loadCorpusManifest(corpusDir: Path): CorpusManifest {
    val path = corpusDir.resolve("manifest.json")
    require(Files.isRegularFile(path)) { "Corpus manifest not found: $path" }
    return runtimeJson.decodeFromString(Files.readString(path))
}

/** Loads the local model-bundle manifest used for query embedding. */
fun loadRuntimeModelManifest(modelDir: Path): RuntimeModelManifest {
    val path = modelDir.resolve("model-manifest.json")
    require(Files.isRegularFile(path)) { "Runtime model manifest not found: $path" }
    return runtimeJson.decodeFromString(Files.readString(path))
}

/**
 * Rejects corpus/model combinations that could produce semantically invalid query vectors.
 *
 * The check is intentionally strict: a matching vector dimension alone is insufficient if model identity,
 * normalization, E5 query prefix, pooling behavior, or persisted corpus format differs. Failing before model/session
 * startup makes configuration drift explicit instead of returning plausible but unrelated literary passages.
 */
fun validateRuntimeCompatibility(corpus: CorpusManifest, model: RuntimeModelManifest) {
    require(corpus.formatVersion == 3) {
        "Unsupported corpus format ${corpus.formatVersion}; Desktop currently supports format 3"
    }
    require(model.schemaVersion == 1) { "Unsupported runtime model manifest ${model.schemaVersion}" }
    require(corpus.embedding.modelId == model.modelId) {
        "Corpus model ${corpus.embedding.modelId} does not match runtime model ${model.modelId}"
    }
    require(corpus.embedding.dimensions == model.dimensions) {
        "Corpus dimensions ${corpus.embedding.dimensions} do not match runtime model ${model.dimensions}"
    }
    require(corpus.embedding.normalize == model.normalize) {
        "Corpus normalization and runtime model normalization do not match"
    }
    require(corpus.embedding.queryPrefix.isNotBlank()) {
        "Corpus manifest has no query_prefix. Rebuild it with the current real-text config."
    }
    require(corpus.embedding.queryPrefix == model.queryPrefix) {
        "Corpus query_prefix does not match runtime model query_prefix"
    }
    require(model.pooling == "mean") { "Unsupported runtime pooling mode: ${model.pooling}" }
}
