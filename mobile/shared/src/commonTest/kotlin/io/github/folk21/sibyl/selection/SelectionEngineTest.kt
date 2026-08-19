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


    @Test
    fun `guided policy keeps low strength curated candidates eligible`() {
        val engine = SelectionEngine(RandomSource { 0.99 })
        val answer = engine.select(
            question = "guided prompt",
            candidates = listOf(candidate("strong", 0.90), candidate("low", 0.05)),
            policy = SelectionPolicy.guidedDefaults(),
        )

        assertEquals("low", answer?.passage?.id)
        assertEquals("guided prompt", answer?.question)
    }

    @Test
    fun `guided strength changes probability without forcing top one`() {
        val candidates = listOf(candidate("strong", 0.90), candidate("weaker", 0.40))
        val strong = SelectionEngine(RandomSource { 0.0 }).select(
            question = "guided",
            candidates = candidates,
            policy = SelectionPolicy.guidedDefaults(),
        )
        val weaker = SelectionEngine(RandomSource { 0.99 }).select(
            question = "guided",
            candidates = candidates,
            policy = SelectionPolicy.guidedDefaults(),
        )

        assertEquals("strong", strong?.passage?.id)
        assertEquals("weaker", weaker?.passage?.id)
    }

    @Test
    fun `guided selection does not permanently blacklist a repeated passage`() {
        val engine = SelectionEngine(RandomSource { 0.0 })
        val candidates = listOf(candidate("repeatable", 0.90), candidate("other", 0.50))

        val first = engine.select(
            question = "guided",
            candidates = candidates,
            policy = SelectionPolicy.guidedDefaults(),
        )
        val second = engine.select(
            question = "guided",
            candidates = candidates,
            policy = SelectionPolicy.guidedDefaults(),
        )

        assertEquals("repeatable", first?.passage?.id)
        assertEquals("repeatable", second?.passage?.id)
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
