package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.GuidedQuestion
import io.github.folk21.sibyl.domain.Passage
import io.github.folk21.sibyl.domain.PassageLength
import io.github.folk21.sibyl.domain.PassageText
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.domain.PassageVariant
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.test.runTest

/** Verifies guided retrieval stays ID-based, deterministic, and independent from embedding contracts. */
class LocalGuidedRetrievalServiceTest {
    @Test
    fun `returns mapped questions and deterministic distinct candidates`() = runTest {
        val service = LocalGuidedRetrievalService(
            repository = object : GuidedCorpusRepository {
                override suspend fun availableQuestions() = listOf(
                    GuidedQuestion("a", "Question A"),
                    GuidedQuestion("c", "Question C"),
                )

                override suspend fun candidates(questionId: String, limit: Int) = listOf(
                    candidate("low", 0.10),
                    candidate("high", 0.90),
                    candidate("high", 0.80),
                )
            },
        )

        assertEquals(listOf("a", "c"), service.availableQuestions().map { it.id })
        val candidates = service.candidates("a", limit = 10)
        assertEquals(listOf("high", "low"), candidates.map { it.passage.id })
        assertEquals(listOf(0.90, 0.10), candidates.map { it.semanticScore })
    }

    @Test
    fun `unknown question remains empty without fallback retrieval`() = runTest {
        val service = LocalGuidedRetrievalService(
            repository = object : GuidedCorpusRepository {
                override suspend fun availableQuestions() = emptyList<GuidedQuestion>()
                override suspend fun candidates(questionId: String, limit: Int) = emptyList<Candidate>()
            },
        )

        assertEquals(emptyList(), service.candidates("missing", 5))
    }

    private fun candidate(id: String, score: Double): Candidate = Candidate(
        passage = Passage(
            id = id,
            author = "Fixture",
            work = "Fixture work",
            location = null,
            originalLanguage = "en",
            variants = mapOf(
                PassageLength.STANDARD to PassageVariant(
                    PassageLength.STANDARD,
                    listOf(PassageText("en", PassageTextRole.ORIGINAL, "Stored $id")),
                ),
            ),
        ),
        semanticScore = score,
    )
}
