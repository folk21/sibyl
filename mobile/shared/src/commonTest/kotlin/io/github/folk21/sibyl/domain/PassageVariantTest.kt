package io.github.folk21.sibyl.domain

import kotlin.test.Test
import kotlin.test.assertEquals

/** Verifies stored original/translation display selection without runtime text generation. */
class PassageVariantTest {
    @Test
    fun `parallel display keeps original and preferred machine translation`() {
        val variant = PassageVariant(
            PassageLength.STANDARD,
            listOf(
                PassageText("en", PassageTextRole.ORIGINAL, "Exact original."),
                PassageText(
                    "ru",
                    PassageTextRole.MACHINE_TRANSLATION,
                    "Сохранённый перевод.",
                    translationProvider = "provider",
                    translationModel = "model",
                ),
            ),
        )

        assertEquals(
            listOf(PassageTextRole.ORIGINAL, PassageTextRole.MACHINE_TRANSLATION),
            variant.parallelDisplayTexts("ru").map { it.role },
        )
    }

    @Test
    fun `same language original is displayed once`() {
        val original = PassageText("ru", PassageTextRole.ORIGINAL, "Точный оригинал.")
        val variant = PassageVariant(PassageLength.STANDARD, listOf(original))

        assertEquals(listOf(original), variant.parallelDisplayTexts("ru"))
    }

    @Test
    fun `human translation is preferred over machine translation`() {
        val variant = PassageVariant(
            PassageLength.STANDARD,
            listOf(
                PassageText("en", PassageTextRole.ORIGINAL, "Exact original."),
                PassageText("ru", PassageTextRole.MACHINE_TRANSLATION, "Машинный."),
                PassageText("ru", PassageTextRole.HUMAN_TRANSLATION, "Человеческий."),
            ),
        )

        assertEquals(
            PassageTextRole.HUMAN_TRANSLATION,
            variant.parallelDisplayTexts("ru").last().role,
        )
    }
}
