package io.github.folk21.sibyl.domain

enum class PassageLength {
    SHORT,
    STANDARD,
    EXTENDED,
}

enum class WorkCategory {
    LITERATURE,
    PHILOSOPHY,
    SACRED_TEXT,
}

enum class PassageTextRole {
    ORIGINAL,
    HUMAN_TRANSLATION,
    MACHINE_TRANSLATION,
}

data class PassageText(
    val language: String,
    val role: PassageTextRole,
    val text: String,
    val translator: String? = null,
    val translationProvider: String? = null,
    val translationModel: String? = null,
)

data class PassageVariant(
    val length: PassageLength,
    val texts: List<PassageText>,
) {
    init {
        require(texts.isNotEmpty()) { "Passage variant must contain at least one text version" }
    }

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

data class Passage(
    val id: String,
    val author: String,
    val work: String,
    val location: String?,
    val originalLanguage: String,
    val category: WorkCategory = WorkCategory.LITERATURE,
    val variants: Map<PassageLength, PassageVariant>,
)

data class Candidate(
    val passage: Passage,
    val semanticScore: Double,
    val qualityScore: Double = 1.0,
    val historyWeight: Double = 1.0,
    val diversityWeight: Double = 1.0,
)

data class Answer(
    val question: String,
    val passage: Passage,
    val variant: PassageVariant,
)

data class SavedEncounter(
    val id: String,
    val question: String,
    val passageId: String,
    val note: String? = null,
)
