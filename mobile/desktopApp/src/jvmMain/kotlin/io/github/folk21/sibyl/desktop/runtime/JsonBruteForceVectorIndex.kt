package io.github.folk21.sibyl.desktop.runtime

import io.github.folk21.sibyl.retrieval.VectorIndex
import io.github.folk21.sibyl.retrieval.VectorMatch
import java.nio.file.Files
import java.nio.file.Path
import kotlin.math.sqrt
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/**
 * Development vector index that loads every semantic-hint vector from `vectors.json` into memory.
 *
 * Search is deliberately exhaustive: every stored vector is scored by cosine similarity, sorted, and truncated to
 * the requested limit. Vector norms are precomputed at load time so repeated queries avoid redundant work. This is
 * simple and deterministic for small Desktop corpora, but it is intentionally behind `VectorIndex` so a production
 * ANN implementation can replace the O(N) scan without changing shared retrieval or UI code.
 */
class JsonBruteForceVectorIndex(
    vectorsPath: Path,
    private val dimensions: Int,
) : VectorIndex {
    /** Cached vector entry with a precomputed norm for repeated query scoring. */
    private data class Entry(
        val hintId: String,
        val vector: FloatArray,
        val norm: Double,
    )

    private val entries: List<Entry> = loadEntries(vectorsPath)

    /**
     * Scores the query against every stored hint vector and returns the strongest cosine matches.
     *
     * Dimension and non-zero-norm checks fail early because silently comparing incompatible embedding spaces would
     * produce plausible-looking but invalid retrieval results.
     */
    override suspend fun search(vector: FloatArray, limit: Int): List<VectorMatch> {
        require(vector.size == dimensions) {
            "Query vector has ${vector.size} dimensions; expected $dimensions"
        }
        require(limit > 0) { "limit must be positive" }
        val queryNorm = norm(vector)
        require(queryNorm > 0.0) { "Query embedding must have a non-zero norm" }

        return entries.asSequence()
            .map { entry ->
                var dot = 0.0
                for (index in 0 until dimensions) {
                    dot += vector[index] * entry.vector[index]
                }
                VectorMatch(entry.hintId, dot / (queryNorm * entry.norm))
            }
            .sortedByDescending(VectorMatch::score)
            .take(limit)
            .toList()
    }

    /** Loads and validates the complete JSON vector artifact once when the index is constructed. */
    private fun loadEntries(path: Path): List<Entry> {
        require(Files.isRegularFile(path)) { "Vector artifact not found: $path" }
        val root = Json.parseToJsonElement(Files.readString(path)).jsonObject
        return root.map { (hintId, value) ->
            val vector = value.jsonArray.map { it.jsonPrimitive.content.toFloat() }.toFloatArray()
            require(vector.size == dimensions) {
                "Vector $hintId has ${vector.size} dimensions; expected $dimensions"
            }
            val vectorNorm = norm(vector)
            require(vectorNorm > 0.0) { "Vector $hintId has a zero norm" }
            Entry(hintId, vector, vectorNorm)
        }
    }

    private fun norm(vector: FloatArray): Double {
        var sum = 0.0
        for (value in vector) {
            sum += value * value
        }
        return sqrt(sum)
    }
}
