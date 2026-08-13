package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate

interface CorpusRepository {
    suspend fun resolve(matches: List<VectorMatch>): List<Candidate>
}

class LocalRetrievalService(
    private val embeddingEngine: EmbeddingEngine,
    private val vectorIndex: VectorIndex,
    private val corpusRepository: CorpusRepository,
    private val retrievalMultiplier: Int = 4,
) : RetrievalService {
    init {
        require(retrievalMultiplier > 0) { "retrievalMultiplier must be positive" }
    }

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
