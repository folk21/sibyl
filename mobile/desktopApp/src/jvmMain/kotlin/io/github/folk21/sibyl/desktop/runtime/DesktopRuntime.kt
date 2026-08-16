package io.github.folk21.sibyl.desktop.runtime

import io.github.folk21.sibyl.retrieval.LocalRetrievalService
import io.github.folk21.sibyl.retrieval.RetrievalService
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths

/**
 * Owns the Desktop-only resources required for real local corpus retrieval.
 *
 * The factory validates corpus/model manifests before opening expensive native resources, then wires the shared
 * `LocalRetrievalService` to JVM implementations for ONNX query embedding, brute-force vector search, and SQLite
 * passage hydration. The runtime owns the closeable embedding engine and database connection for the full window
 * lifetime; partial initialization is cleaned up before an exception escapes.
 */
class DesktopRuntime private constructor(
    val retrievalService: RetrievalService,
    val label: String,
    private val embeddingEngine: OnnxE5EmbeddingEngine,
    private val repository: SqliteCorpusRepository,
) : AutoCloseable {
    override fun close() {
        repository.close()
        embeddingEngine.close()
    }

    companion object {
        /**
         * Loads one published corpus and a compatible local embedding-model bundle.
         *
         * Manifest compatibility is checked before inference starts so model ID, dimensions, normalization, E5
         * query prefix, pooling, and corpus format cannot drift silently. Resource construction is ordered so every
         * successfully opened resource is closed if a later adapter fails to initialize.
         */
        fun load(corpusDir: Path, modelDir: Path): DesktopRuntime {
            require(Files.isDirectory(corpusDir)) { "Corpus directory not found: $corpusDir" }
            require(Files.isDirectory(modelDir)) { "Runtime model directory not found: $modelDir" }

            val corpusManifest = loadCorpusManifest(corpusDir)
            val modelManifest = loadRuntimeModelManifest(modelDir)
            validateRuntimeCompatibility(corpusManifest, modelManifest)

            val embeddingEngine = OnnxE5EmbeddingEngine(
                modelPath = modelDir.resolve(modelManifest.modelFile),
                tokenizerPath = modelDir.resolve(modelManifest.tokenizerFile),
                dimensions = modelManifest.dimensions,
                queryPrefix = modelManifest.queryPrefix,
                maxLength = modelManifest.maxLength,
                normalize = modelManifest.normalize,
            )
            try {
                val vectorIndex = JsonBruteForceVectorIndex(
                    vectorsPath = corpusDir.resolve(corpusManifest.artifacts.vectors),
                    dimensions = corpusManifest.embedding.dimensions,
                )
                val repository = SqliteCorpusRepository(
                    corpusDir.resolve(corpusManifest.artifacts.corpus),
                )
                return try {
                    DesktopRuntime(
                        retrievalService = LocalRetrievalService(
                            embeddingEngine = embeddingEngine,
                            vectorIndex = vectorIndex,
                            corpusRepository = repository,
                        ),
                        label = "${corpusManifest.counts.works} works · ${corpusManifest.counts.passages} passages",
                        embeddingEngine = embeddingEngine,
                        repository = repository,
                    )
                } catch (error: Throwable) {
                    repository.close()
                    throw error
                }
            } catch (error: Throwable) {
                embeddingEngine.close()
                throw error
            }
        }
    }
}

/**
 * Resolved filesystem locations for an optional real-corpus Desktop session.
 *
 * Desktop treats the two paths as an atomic configuration: both must be present for real retrieval, while absence
 * of both selects the synthetic demo. This avoids accidentally pairing a real corpus with an implicit/default model.
 */
data class DesktopRuntimePaths(
    val corpusDir: Path,
    val modelDir: Path,
) {
    companion object {
        /** Returns configured runtime paths, or null when Desktop should use demo mode. */
        fun fromEnvironment(): DesktopRuntimePaths? {
            val corpus = System.getenv("SIBYL_CORPUS_DIR")?.takeIf { it.isNotBlank() }
            val model = System.getenv("SIBYL_MODEL_DIR")?.takeIf { it.isNotBlank() }
            if (corpus == null && model == null) return null
            require(corpus != null && model != null) {
                "Set both SIBYL_CORPUS_DIR and SIBYL_MODEL_DIR, or neither for demo mode"
            }
            return DesktopRuntimePaths(
                Paths.get(corpus).toAbsolutePath(),
                Paths.get(model).toAbsolutePath(),
            )
        }
    }
}
