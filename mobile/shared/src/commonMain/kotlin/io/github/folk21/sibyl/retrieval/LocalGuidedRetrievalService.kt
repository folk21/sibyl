package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.GuidedQuestion

/**
 * Normalizes a local guided repository into the shared guided-retrieval contract.
 *
 * The service performs no embedding and no final selection. It keeps distinct passages, retains the strongest
 * mapping score if a repository ever returns duplicates, sorts deterministically by curated relevance and passage
 * ID, and applies the requested candidate limit.
 */
class LocalGuidedRetrievalService(
    private val repository: GuidedCorpusRepository,
) : GuidedRetrievalService {
    override suspend fun availableQuestions(): List<GuidedQuestion> = repository.availableQuestions()

    /** Returns a deterministic candidate pool while preserving every validated strength as an eligible score. */
    override suspend fun candidates(questionId: String, limit: Int): List<Candidate> {
        require(questionId.isNotBlank()) { "questionId must not be blank" }
        require(limit > 0) { "limit must be positive" }
        return repository.candidates(questionId, limit)
            .groupBy { it.passage.id }
            .mapNotNull { (_, candidates) -> candidates.maxByOrNull { it.semanticScore } }
            .sortedWith(compareByDescending<Candidate> { it.semanticScore }.thenBy { it.passage.id })
            .take(limit)
    }
}
