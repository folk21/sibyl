package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate

/** Encodes runtime query text into the corpus embedding space. */
interface EmbeddingEngine {
    suspend fun embed(text: String): FloatArray
}

/** Similarity result linking a vector hit to one internal semantic hint. */
data class VectorMatch(
    val hintId: String,
    val score: Double,
)

/** Retrieves multiple plausible semantic matches rather than a single nearest passage. */
interface VectorIndex {
    suspend fun search(vector: FloatArray, limit: Int): List<VectorMatch>
}

/** Produces a ranked candidate pool while leaving final serendipitous choice to selection. */
interface RetrievalService {
    suspend fun candidates(question: String, limit: Int): List<Candidate>
}
