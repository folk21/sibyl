package io.github.folk21.sibyl.demo

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.Passage
import io.github.folk21.sibyl.domain.PassageLength
import io.github.folk21.sibyl.domain.PassageText
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.domain.PassageVariant
import io.github.folk21.sibyl.retrieval.RetrievalService

/** Supplies clearly synthetic candidates for UI development without a real corpus. */
class DemoRetrievalService : RetrievalService {
    override suspend fun candidates(question: String, limit: Int): List<Candidate> = demoCandidates.take(limit)

    private fun original(text: String) = PassageText(
        language = "en",
        role = PassageTextRole.ORIGINAL,
        text = text,
    )

    private val demoCandidates = listOf(
        Candidate(
            passage = Passage(
                id = "demo-road",
                author = "Synthetic fixture",
                work = "The Road",
                location = "Test corpus",
                originalLanguage = "en",
                variants = mapOf(
                    PassageLength.SHORT to PassageVariant(
                        PassageLength.SHORT,
                        listOf(original("The road became visible only after the traveller stepped onto it.")),
                    ),
                    PassageLength.STANDARD to PassageVariant(
                        PassageLength.STANDARD,
                        listOf(original("The traveller waited for the whole road to become visible. Only after the first step did the next turn appear.")),
                    ),
                ),
            ),
            semanticScore = 0.77,
            qualityScore = 0.95,
        ),
        Candidate(
            passage = Passage(
                id = "demo-window",
                author = "Synthetic fixture",
                work = "The Window",
                location = "Test corpus",
                originalLanguage = "en",
                variants = mapOf(
                    PassageLength.SHORT to PassageVariant(
                        PassageLength.SHORT,
                        listOf(original("Nothing outside had changed, but the window was open now.")),
                    ),
                ),
            ),
            semanticScore = 0.66,
            qualityScore = 0.90,
        ),
        Candidate(
            passage = Passage(
                id = "demo-lamp",
                author = "Synthetic fixture",
                work = "The Lamp",
                location = "Test corpus",
                originalLanguage = "en",
                variants = mapOf(
                    PassageLength.SHORT to PassageVariant(
                        PassageLength.SHORT,
                        listOf(original("He lit one lamp and stopped asking how he would illuminate the whole house.")),
                    ),
                ),
            ),
            semanticScore = 0.71,
            qualityScore = 0.92,
        ),
    )
}
