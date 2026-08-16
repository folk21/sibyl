package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate

/**
 * Resolves internal semantic-hint matches to stored literary passage candidates.
 *
 * Vector hits are retrieval metadata, not display text. Implementations hydrate the owning passage and its
 * prepared text variants from the corpus so the later selection/UI stages can only return persisted text.
 */
interface CorpusRepository {
    suspend fun resolve(matches: List<VectorMatch>): List<Candidate>
}

/**
 * Coordinates the shared local retrieval pipeline without making the final answer choice.
 *
 * A query is embedded once, then the vector index is intentionally asked for a wider semantic-hint pool than
 * the requested passage count. Several hints may reference the same passage, so hydrated candidates are grouped
 * by passage ID and only the strongest semantic score is retained before the final limit is applied.
 *
 * This class stops at a relevance-ranked candidate pool. Controlled serendipity remains the responsibility of
 * `SelectionEngine`, which prevents the runtime from collapsing into top-1 nearest-neighbor lookup.
 */
class LocalRetrievalService(
    private val embeddingEngine: EmbeddingEngine,
    private val vectorIndex: VectorIndex,
    private val corpusRepository: CorpusRepository,
    private val retrievalMultiplier: Int = 4,
) : RetrievalService {
    init {
        require(retrievalMultiplier > 0) { "retrievalMultiplier must be positive" }
    }

    /**
     * Produces at most [limit] distinct passages for [question].
     *
     * Retrieval expands the vector-search limit before corpus hydration, then deduplicates by passage and keeps
     * the strongest matching hint score. The returned order is relevance order only; callers must still delegate
     * the final passage choice to the selection stage.
     */
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
