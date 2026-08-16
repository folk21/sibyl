package io.github.folk21.sibyl.domain

/** Selects one prepared passage-length variant; runtime never truncates literary text. */
enum class PassageLength {
    SHORT,
    STANDARD,
    EXTENDED,
}

/** Classifies corpus works without changing the retrieval engine. */
enum class WorkCategory {
    LITERATURE,
    PHILOSOPHY,
    SACRED_TEXT,
}

/** Identifies whether displayed text is original or a human/machine translation. */
enum class PassageTextRole {
    ORIGINAL,
    HUMAN_TRANSLATION,
    MACHINE_TRANSLATION,
}

/** One exact stored text realization of a passage in a concrete language and role. */
data class PassageText(
    val language: String,
    val role: PassageTextRole,
    val text: String,
    val translator: String? = null,
    val translationProvider: String? = null,
    val translationModel: String? = null,
)

/** Groups all text versions available for one prepared passage length. */
data class PassageVariant(
    val length: PassageLength,
    val texts: List<PassageText>,
) {
    init {
        require(texts.isNotEmpty()) { "Passage variant must contain at least one text version" }
    }

    /**
     * Chooses stored display text by preferred language first, then by original/human/machine role priority.
     *
     * The method only selects among existing text versions; it never translates or rewrites a passage at runtime.
     */
    fun preferredText(language: String = "ru"): PassageText {
        val preferredLanguage = texts.filter { it.language == language }
        return preferredLanguage.minByOrNull { it.role.displayPriority() }
            ?: texts.minByOrNull { it.role.displayPriority() }
            ?: error("Passage variant must contain at least one text version")
    }
}

private fun PassageTextRole.displayPriority(): Int = when (this) {
    PassageTextRole.ORIGINAL -> 0
    PassageTextRole.HUMAN_TRANSLATION -> 1
    PassageTextRole.MACHINE_TRANSLATION -> 2
}

/** Runtime literary passage with immutable metadata and prepared display variants. */
data class Passage(
    val id: String,
    val author: String,
    val work: String,
    val location: String?,
    val originalLanguage: String,
    val category: WorkCategory = WorkCategory.LITERATURE,
    val variants: Map<PassageLength, PassageVariant>,
)

/** Retrieved passage plus independent weights consumed by controlled-random selection. */
data class Candidate(
    val passage: Passage,
    val semanticScore: Double,
    val qualityScore: Double = 1.0,
    val historyWeight: Double = 1.0,
    val diversityWeight: Double = 1.0,
)

/** Selected encounter returned to the UI with the original user question. */
data class Answer(
    val question: String,
    val passage: Passage,
    val variant: PassageVariant,
)

/** Persistable reference that explicitly preserves a user question and chosen passage. */
data class SavedEncounter(
    val id: String,
    val question: String,
    val passageId: String,
    val note: String? = null,
)
