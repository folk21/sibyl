package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate

/** Resolves internal vector matches to exact stored literary passage candidates. */
interface CorpusRepository {
    suspend fun resolve(matches: List<VectorMatch>): List<Candidate>
}

/** Coordinates local query embedding, vector retrieval, hydration, and passage deduplication. */
class LocalRetrievalService(
    private val embeddingEngine: EmbeddingEngine,
    private val vectorIndex: VectorIndex,
    private val corpusRepository: CorpusRepository,
    private val retrievalMultiplier: Int = 4,
) : RetrievalService {
    init {
        require(retrievalMultiplier > 0) { "retrievalMultiplier must be positive" }
    }

    /** Retrieves a wider hint pool, resolves passages, and keeps the strongest score per passage. */
    override suspend fun candidates(question: String, limit: Int): List<Candidate> {
        require(limit > 0) { "limit must be positive" }
        val queryVector = embeddingEngine.embed(question)
        val matches = vectorIndex.search(queryVector, limit * retrievalMultiplier)
        return corpusRepository.resolve(matches)
            .groupBy { it.passage.id }
            .mapNotNull { (_, candidates) -> candidates.maxByOrNull { it.semanticScore } }
            .sortedByDescending { it.semanticScore }
            .take(limit)
    }
}
