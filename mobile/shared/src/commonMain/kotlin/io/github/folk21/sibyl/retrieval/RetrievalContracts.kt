package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate

interface EmbeddingEngine {
    suspend fun embed(text: String): FloatArray
}

data class VectorMatch(
    val hintId: String,
    val score: Double,
)

interface VectorIndex {
    suspend fun search(vector: FloatArray, limit: Int): List<VectorMatch>
}

interface RetrievalService {
    suspend fun candidates(question: String, limit: Int): List<Candidate>
}
