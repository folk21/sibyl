package io.github.folk21.sibyl.desktop.runtime

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.Passage
import io.github.folk21.sibyl.domain.PassageLength
import io.github.folk21.sibyl.domain.PassageText
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.domain.PassageVariant
import io.github.folk21.sibyl.domain.WorkCategory
import io.github.folk21.sibyl.retrieval.CorpusRepository
import io.github.folk21.sibyl.retrieval.VectorMatch
import java.nio.file.Files
import java.nio.file.Path
import java.sql.Connection
import org.sqlite.SQLiteConfig

class SqliteCorpusRepository(corpusPath: Path) : CorpusRepository, AutoCloseable {
    private data class PassageBuilder(
        val id: String,
        val author: String,
        val work: String,
        val location: String?,
        val originalLanguage: String,
        val category: WorkCategory,
        var semanticScore: Double,
        val qualityScore: Double,
        val variants: MutableMap<PassageLength, LinkedHashMap<String, PassageText>> = linkedMapOf(),
    )

    private val connection: Connection

    init {
        require(Files.isRegularFile(corpusPath)) { "Corpus database not found: $corpusPath" }
        val config = SQLiteConfig().apply { setReadOnly(true) }
        connection = config.createConnection("jdbc:sqlite:${corpusPath.toAbsolutePath()}")
    }

    override suspend fun resolve(matches: List<VectorMatch>): List<Candidate> {
        if (matches.isEmpty()) return emptyList()
        val scoreByHint = matches.associate { it.hintId to it.score }
        val placeholders = List(scoreByHint.size) { "?" }.joinToString(",")
        val sql = """
            SELECT
                sh.id AS hint_id,
                p.id AS passage_id,
                p.source_locator,
                p.quality_score,
                w.title AS work_title,
                w.original_language,
                w.category,
                a.display_name AS author_name,
                pt.variant,
                pt.text,
                tv.id AS text_version_id,
                tv.language,
                tv.role,
                tv.translator,
                tv.translation_provider,
                tv.translation_model
            FROM semantic_hint sh
            JOIN passage p ON p.id = sh.passage_id
            JOIN work w ON w.id = p.work_id
            JOIN author a ON a.id = w.author_id
            JOIN passage_text pt ON pt.passage_id = p.id
            JOIN text_version tv ON tv.id = pt.text_version_id
            WHERE sh.id IN ($placeholders)
        """.trimIndent()

        val builders = linkedMapOf<String, PassageBuilder>()
        connection.prepareStatement(sql).use { statement ->
            scoreByHint.keys.forEachIndexed { index, hintId -> statement.setString(index + 1, hintId) }
            statement.executeQuery().use { rows ->
                while (rows.next()) {
                    val hintId = rows.getString("hint_id")
                    val passageId = rows.getString("passage_id")
                    val semanticScore = scoreByHint.getValue(hintId)
                    val quality = rows.getDouble("quality_score").let { value ->
                        if (rows.wasNull()) 1.0 else value
                    }
                    val builder = builders.getOrPut(passageId) {
                        PassageBuilder(
                            id = passageId,
                            author = rows.getString("author_name"),
                            work = rows.getString("work_title"),
                            location = rows.getString("source_locator"),
                            originalLanguage = rows.getString("original_language"),
                            category = rows.getString("category").toWorkCategory(),
                            semanticScore = semanticScore,
                            qualityScore = quality,
                        )
                    }
                    builder.semanticScore = maxOf(builder.semanticScore, semanticScore)
                    val length = rows.getString("variant").toPassageLength()
                    val texts = builder.variants.getOrPut(length) { linkedMapOf() }
                    val textVersionId = rows.getString("text_version_id")
                    texts.putIfAbsent(
                        textVersionId,
                        PassageText(
                            language = rows.getString("language"),
                            role = rows.getString("role").toPassageTextRole(),
                            text = rows.getString("text"),
                            translator = rows.getString("translator"),
                            translationProvider = rows.getString("translation_provider"),
                            translationModel = rows.getString("translation_model"),
                        ),
                    )
                }
            }
        }

        return builders.values.map { builder ->
            val passage = Passage(
                id = builder.id,
                author = builder.author,
                work = builder.work,
                location = builder.location,
                originalLanguage = builder.originalLanguage,
                category = builder.category,
                variants = builder.variants.mapValues { (length, texts) ->
                    PassageVariant(length = length, texts = texts.values.toList())
                },
            )
            Candidate(
                passage = passage,
                semanticScore = builder.semanticScore,
                qualityScore = builder.qualityScore,
            )
        }
    }

    override fun close() {
        connection.close()
    }
}

private fun String.toWorkCategory(): WorkCategory = when (this) {
    "literature" -> WorkCategory.LITERATURE
    "philosophy" -> WorkCategory.PHILOSOPHY
    "sacred_text" -> WorkCategory.SACRED_TEXT
    else -> error("Unsupported work category: $this")
}

private fun String.toPassageLength(): PassageLength = when (this) {
    "short" -> PassageLength.SHORT
    "standard" -> PassageLength.STANDARD
    "extended" -> PassageLength.EXTENDED
    else -> error("Unsupported passage variant: $this")
}

private fun String.toPassageTextRole(): PassageTextRole = when (this) {
    "original" -> PassageTextRole.ORIGINAL
    "human_translation" -> PassageTextRole.HUMAN_TRANSLATION
    "machine_translation" -> PassageTextRole.MACHINE_TRANSLATION
    else -> error("Unsupported passage text role: $this")
}
