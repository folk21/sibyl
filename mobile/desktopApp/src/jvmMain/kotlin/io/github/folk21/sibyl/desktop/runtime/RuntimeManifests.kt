package io.github.folk21.sibyl.desktop.runtime

import java.nio.file.Files
import java.nio.file.Path
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

private val runtimeJson = Json { ignoreUnknownKeys = true }

@Serializable
data class CorpusEmbeddingManifest(
    val provider: String,
    @SerialName("model_id") val modelId: String? = null,
    val dimensions: Int,
    val normalize: Boolean,
    @SerialName("passage_prefix") val passagePrefix: String = "",
    @SerialName("query_prefix") val queryPrefix: String = "",
)

@Serializable
data class CorpusArtifactsManifest(
    val corpus: String,
    val vectors: String,
)

@Serializable
data class CorpusCountsManifest(
    val works: Int,
    val passages: Int,
    val hints: Int,
)

@Serializable
data class CorpusManifest(
    @SerialName("format_version") val formatVersion: Int,
    val embedding: CorpusEmbeddingManifest,
    val artifacts: CorpusArtifactsManifest,
    val counts: CorpusCountsManifest,
)

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

fun loadCorpusManifest(corpusDir: Path): CorpusManifest {
    val path = corpusDir.resolve("manifest.json")
    require(Files.isRegularFile(path)) { "Corpus manifest not found: $path" }
    return runtimeJson.decodeFromString(Files.readString(path))
}

fun loadRuntimeModelManifest(modelDir: Path): RuntimeModelManifest {
    val path = modelDir.resolve("model-manifest.json")
    require(Files.isRegularFile(path)) { "Runtime model manifest not found: $path" }
    return runtimeJson.decodeFromString(Files.readString(path))
}

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
