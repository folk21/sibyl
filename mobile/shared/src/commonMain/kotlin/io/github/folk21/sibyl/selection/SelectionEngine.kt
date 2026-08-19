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

/**
 * Controls semantic eligibility, weighting shape, and preferred prepared passage length.
 *
 * The semantic exponent changes how strongly high-similarity candidates are favored after the minimum relevance
 * gate. Other candidate weights remain independent so history/diversity/quality can influence probability without
 * replacing semantic relevance or permanently excluding previously seen passages.
 */
data class SelectionPolicy(
    val minSemanticScore: Double,
    val semanticExponent: Double,
    val preferredLength: PassageLength,
) {
    companion object {
        /** Default policy for free-form semantic retrieval. */
        fun defaults(): SelectionPolicy = SelectionPolicy(
            minSemanticScore = 0.20,
            semanticExponent = 1.5,
            preferredLength = PassageLength.SHORT,
        )

        /** Guided mappings are prevalidated relevance gates, so no additional semantic threshold is applied. */
        fun guidedDefaults(): SelectionPolicy = defaults().copy(minSemanticScore = 0.0)
    }
}

/**
 * Selects one eligible passage by weighted random sampling instead of returning the nearest vector match.
 *
 * Selection first applies the semantic threshold and passage-level deduplication. Each surviving candidate gets
 * a non-negative weight composed from semantic relevance, quality, history, and diversity. A random cursor is then
 * sampled across the cumulative weight range, making more relevant passages more likely while preserving product
 * serendipity. Injected [RandomSource] keeps the exact choice deterministic in tests.
 *
 * The engine never truncates literary text. After a passage is chosen it selects an already prepared length
 * variant, falling back to STANDARD and then to any available stored variant.
 */
class SelectionEngine(
    private val randomSource: RandomSource = RandomSource { Random.nextDouble() },
) {
    /**
     * Applies the selection policy and returns one stored passage encounter, or `null` when nothing is eligible.
     *
     * A zero total weight uses the first eligible candidate as a deterministic safety fallback rather than
     * attempting an invalid random distribution. Literary content is returned through an existing `PassageVariant`
     * only; this method never creates, summarizes, or truncates passage text.
     */
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
