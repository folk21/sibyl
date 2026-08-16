package io.github.folk21.sibyl.selection

import io.github.folk21.sibyl.domain.Answer
import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.PassageLength
import kotlin.math.pow
import kotlin.random.Random

/** Injectable randomness boundary used to make selection deterministic in tests. */
fun interface RandomSource {
    fun nextDouble(): Double
}

/** Controls semantic eligibility, weighting shape, and preferred prepared length. */
data class SelectionPolicy(
    val minSemanticScore: Double,
    val semanticExponent: Double,
    val preferredLength: PassageLength,
) {
    companion object {
        fun defaults(): SelectionPolicy = SelectionPolicy(
            minSemanticScore = 0.20,
            semanticExponent = 1.5,
            preferredLength = PassageLength.SHORT,
        )
    }
}

/** Selects one eligible passage with controlled randomness instead of top-1 ranking. */
class SelectionEngine(
    private val randomSource: RandomSource = RandomSource { Random.nextDouble() },
) {
    /** Filters, weights, samples, and chooses a prepared variant without altering its text. */
    fun select(
        question: String,
        candidates: List<Candidate>,
        policy: SelectionPolicy = SelectionPolicy.defaults(),
    ): Answer? {
        val eligible = candidates
            .filter { it.semanticScore >= policy.minSemanticScore }
            .distinctBy { it.passage.id }

        if (eligible.isEmpty()) return null

        val weighted = eligible.map { candidate ->
            val semantic = candidate.semanticScore.coerceAtLeast(0.0).pow(policy.semanticExponent)
            val weight = semantic *
                candidate.qualityScore.coerceAtLeast(0.0) *
                candidate.historyWeight.coerceAtLeast(0.0) *
                candidate.diversityWeight.coerceAtLeast(0.0)
            candidate to weight
        }

        val total = weighted.sumOf { it.second }
        val selected = if (total <= 0.0) {
            eligible.first()
        } else {
            var cursor = randomSource.nextDouble().coerceIn(0.0, 0.999999999) * total
            weighted.firstOrNull { (_, weight) ->
                cursor -= weight
                cursor <= 0.0
            }?.first ?: weighted.last().first
        }

        val variant = selected.passage.variants[policy.preferredLength]
            ?: selected.passage.variants[PassageLength.STANDARD]
            ?: selected.passage.variants.values.first()

        return Answer(question = question, passage = selected.passage, variant = variant)
    }
}
