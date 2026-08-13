package io.github.folk21.sibyl.desktop.runtime

import java.nio.file.Files
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.runBlocking

class JsonBruteForceVectorIndexTest {
    @Test
    fun ranksByCosineSimilarity() = runBlocking {
        val directory = Files.createTempDirectory("sibyl-vectors")
        val vectors = directory.resolve("vectors.json")
        Files.writeString(vectors, """{"near":[1.0,0.0],"far":[0.0,1.0]}""")
        val index = JsonBruteForceVectorIndex(vectors, dimensions = 2)

        val result = index.search(floatArrayOf(1f, 0f), limit = 2)

        assertEquals("near", result.first().hintId)
        assertEquals(1.0, result.first().score, absoluteTolerance = 1e-6)
    }
}
