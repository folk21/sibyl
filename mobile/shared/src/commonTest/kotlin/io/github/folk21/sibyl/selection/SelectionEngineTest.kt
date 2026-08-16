package io.github.folk21.sibyl.selection

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.Passage
import io.github.folk21.sibyl.domain.PassageLength
import io.github.folk21.sibyl.domain.PassageText
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.domain.PassageVariant
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

/** Verifies deterministic eligibility, deduplication, and controlled-random selection. */
class SelectionEngineTest {
    @Test
    fun `filters candidates below semantic threshold`() {
        val engine = SelectionEngine(RandomSource { 0.0 })
        val answer = engine.select(
            question = "test",
            candidates = listOf(candidate("low", 0.10), candidate("high", 0.70)),
            policy = SelectionPolicy(
                minSemanticScore = 0.20,
                semanticExponent = 1.0,
                preferredLength = PassageLength.SHORT,
            ),
        )

        assertEquals("high", answer?.passage?.id)
    }

    @Test
    fun `returns null when no candidate is eligible`() {
        val engine = SelectionEngine(RandomSource { 0.5 })
        val answer = engine.select(
            question = "test",
            candidates = listOf(candidate("low", 0.10)),
            policy = SelectionPolicy.defaults(),
        )

        assertNull(answer)
    }

    @Test
    fun `deduplicates multiple hints that point to one passage`() {
        val engine = SelectionEngine(RandomSource { 0.99 })
        val repeated = candidate("same", 0.80)
        val other = candidate("other", 0.79)

        val answer = engine.select(
            question = "test",
            candidates = listOf(repeated, repeated.copy(semanticScore = 0.81), other),
            policy = SelectionPolicy(
                minSemanticScore = 0.20,
                semanticExponent = 1.0,
                preferredLength = PassageLength.SHORT,
            ),
        )

        assertEquals("other", answer?.passage?.id)
    }

    private fun candidate(id: String, score: Double): Candidate = Candidate(
        passage = Passage(
            id = id,
            author = "Fixture",
            work = "Fixture work",
            location = null,
            originalLanguage = "en",
            variants = mapOf(
                PassageLength.SHORT to PassageVariant(
                    PassageLength.SHORT,
                    listOf(PassageText("en", PassageTextRole.ORIGINAL, id)),
                ),
            ),
        ),
        semanticScore = score,
    )
}
