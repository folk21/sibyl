package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.GuidedQuestion

/**
 * Encodes runtime query text into the same vector space used by persisted corpus retrieval metadata.
 *
 * Platform adapters own tokenizer/model details; shared retrieval depends only on this stable local contract.
 */
interface EmbeddingEngine {
    suspend fun embed(text: String): FloatArray
}

/** Similarity result linking a vector hit to one internal semantic hint. */
data class VectorMatch(
    val hintId: String,
    val score: Double,
)

/**
 * Retrieves multiple plausible semantic-hint matches from a local vector space.
 *
 * Implementations return hint-level matches rather than directly choosing a passage so shared code can deduplicate,
 * hydrate exact stored text, and preserve a broader candidate pool for controlled-random selection.
 */
interface VectorIndex {
    suspend fun search(vector: FloatArray, limit: Int): List<VectorMatch>
}

/**
 * Produces a relevance-ranked candidate pool for free-form text while leaving final choice to selection.
 *
 * Callers must not treat the first candidate as the product answer; retrieval and selection are separate by design.
 */
interface RetrievalService {
    suspend fun candidates(question: String, limit: Int): List<Candidate>
}

/**
 * Reads persisted guided-question data without interpreting SQLite or curation metadata in shared code.
 *
 * Platform repositories expose only questions that have at least one stored mapping and hydrate candidates from
 * exact persisted passage text. Guided lookup is independent of [EmbeddingEngine] and [VectorIndex].
 */
interface GuidedCorpusRepository {
    suspend fun availableQuestions(): List<GuidedQuestion>
    suspend fun candidates(questionId: String, limit: Int): List<Candidate>
}

/**
 * Produces candidate pools for stable guided-question IDs without invoking semantic embedding.
 *
 * Curated membership is already the relevance gate. Implementations preserve mapping strength as candidate
 * relevance and leave the controlled-random final answer to `SelectionEngine`.
 */
interface GuidedRetrievalService {
    suspend fun availableQuestions(): List<GuidedQuestion>
    suspend fun candidates(questionId: String, limit: Int): List<Candidate>
}
