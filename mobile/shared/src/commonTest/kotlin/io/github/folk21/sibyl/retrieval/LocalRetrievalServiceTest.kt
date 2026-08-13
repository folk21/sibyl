package io.github.folk21.sibyl.retrieval

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.Passage
import io.github.folk21.sibyl.domain.PassageLength
import io.github.folk21.sibyl.domain.PassageText
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.domain.PassageVariant
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.test.runTest

class LocalRetrievalServiceTest {
    @Test
    fun deduplicatesPassagesAndKeepsStrongestSemanticScore() = runTest {
        val passage = Passage(
            id = "passage-1",
            author = "Author",
            work = "Work",
            location = null,
            originalLanguage = "ru",
            variants = mapOf(
                PassageLength.STANDARD to PassageVariant(
                    PassageLength.STANDARD,
                    listOf(PassageText("ru", PassageTextRole.ORIGINAL, "Stored text")),
                ),
            ),
        )
        val service = LocalRetrievalService(
            embeddingEngine = object : EmbeddingEngine {
                override suspend fun embed(text: String) = floatArrayOf(1f, 0f)
            },
            vectorIndex = object : VectorIndex {
                override suspend fun search(vector: FloatArray, limit: Int) = listOf(
                    VectorMatch("hint-low", 0.5),
                    VectorMatch("hint-high", 0.8),
                )
            },
            corpusRepository = object : CorpusRepository {
                override suspend fun resolve(matches: List<VectorMatch>) = listOf(
                    Candidate(passage, semanticScore = matches[0].score),
                    Candidate(passage, semanticScore = matches[1].score),
                )
            },
        )

        val result = service.candidates("question", limit = 10)

        assertEquals(1, result.size)
        assertEquals(0.8, result.single().semanticScore)
    }
}
