package io.github.folk21.sibyl.desktop.runtime

import io.github.folk21.sibyl.domain.Candidate
import io.github.folk21.sibyl.domain.GuidedQuestion
import io.github.folk21.sibyl.domain.Passage
import io.github.folk21.sibyl.domain.PassageLength
import io.github.folk21.sibyl.domain.PassageText
import io.github.folk21.sibyl.domain.PassageTextRole
import io.github.folk21.sibyl.domain.PassageVariant
import io.github.folk21.sibyl.domain.WorkCategory
import io.github.folk21.sibyl.retrieval.CorpusRepository
import io.github.folk21.sibyl.retrieval.GuidedCorpusRepository
import io.github.folk21.sibyl.retrieval.VectorMatch
import java.nio.file.Files
import java.nio.file.Path
import java.sql.Connection
import java.sql.ResultSet
import org.sqlite.SQLiteConfig

/**
 * Hydrates free-form semantic hits and format-v4 guided mappings from one read-only corpus database.
 *
 * Both lookup paths reconstruct immutable passages only from persisted `passage_text.text`. Free-form lookup uses
 * semantic-hint IDs supplied by the vector index, while guided lookup reads `guided_question_passage.strength`
 * directly and therefore performs no embedding or vector search. Format-v3 databases remain valid for free-form
 * resolution; guided methods return no available data without querying tables that do not exist in v3.
 */
class SqliteCorpusRepository(
    corpusPath: Path,
    private val formatVersion: Int,
) : CorpusRepository, GuidedCorpusRepository, AutoCloseable {
    /** Accumulates exact stored variants while joined SQLite rows for one passage are consumed. */
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

    /**
     * Resolves vector matches to exact passage candidates and retains the strongest score per passage.
     *
     * Several semantic hints may point to the same passage. SQL rows are joined to all prepared text variants, then
     * folded by passage ID without normalizing, rewriting, or truncating the persisted literary text.
     */
    override suspend fun resolve(matches: List<VectorMatch>): List<Candidate> {
        if (matches.isEmpty()) return emptyList()
        val scoreByHint = matches.associate { it.hintId to it.score }
        val placeholders = List(scoreByHint.size) { "?" }.joinToString(",")
        val sql = """
            SELECT
                sh.id AS score_key,
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

        connection.prepareStatement(sql).use { statement ->
            scoreByHint.keys.forEachIndexed { index, hintId -> statement.setString(index + 1, hintId) }
            statement.executeQuery().use { rows ->
                return hydrateCandidates(rows) { row -> scoreByHint.getValue(row.getString("score_key")) }
            }
        }
    }

    /** Returns mapped format-v4 guided questions in persisted catalog order; v3 exposes none. */
    override suspend fun availableQuestions(): List<GuidedQuestion> {
        if (formatVersion < 4) return emptyList()
        val sql = """
            SELECT q.id, q.text, q.kind, q.theme
            FROM guided_question q
            WHERE EXISTS (
                SELECT 1
                FROM guided_question_passage gqp
                WHERE gqp.question_id = q.id
            )
            ORDER BY q.catalog_id, q.ordinal, q.id
        """.trimIndent()
        connection.prepareStatement(sql).use { statement ->
            statement.executeQuery().use { rows ->
                val result = mutableListOf<GuidedQuestion>()
                while (rows.next()) {
                    result += GuidedQuestion(
                        id = rows.getString("id"),
                        text = rows.getString("text"),
                        kind = rows.getString("kind"),
                        theme = rows.getString("theme"),
                    )
                }
                return result
            }
        }
    }

    /**
     * Resolves one stable guided-question ID to exact stored passage candidates ordered by curated strength.
     *
     * The limited mapping set is selected before joining passage text so a passage's stored variants cannot consume
     * the candidate limit. Unknown IDs and format-v3 corpora return an empty pool.
     */
    override suspend fun candidates(questionId: String, limit: Int): List<Candidate> {
        require(limit > 0) { "limit must be positive" }
        if (formatVersion < 4) return emptyList()
        val sql = """
            WITH selected AS (
                SELECT passage_id, strength
                FROM guided_question_passage
                WHERE question_id = ?
                ORDER BY strength DESC, passage_id ASC
                LIMIT ?
            )
            SELECT
                selected.passage_id AS score_key,
                selected.strength AS guided_strength,
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
            FROM selected
            JOIN passage p ON p.id = selected.passage_id
            JOIN work w ON w.id = p.work_id
            JOIN author a ON a.id = w.author_id
            JOIN passage_text pt ON pt.passage_id = p.id
            JOIN text_version tv ON tv.id = pt.text_version_id
            ORDER BY selected.strength DESC, p.id, pt.variant, tv.id
        """.trimIndent()
        connection.prepareStatement(sql).use { statement ->
            statement.setString(1, questionId)
            statement.setInt(2, limit)
            statement.executeQuery().use { rows ->
                return hydrateCandidates(rows) { row -> row.getDouble("guided_strength") }
            }
        }
    }

    /** Folds one joined result set into passage candidates while preserving exact stored text values. */
    private fun hydrateCandidates(
        rows: ResultSet,
        score: (ResultSet) -> Double,
    ): List<Candidate> {
        val builders = linkedMapOf<String, PassageBuilder>()
        while (rows.next()) {
            val passageId = rows.getString("passage_id")
            val semanticScore = score(rows)
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

        return builders.values.map { builder ->
            Candidate(
                passage = Passage(
                    id = builder.id,
                    author = builder.author,
                    work = builder.work,
                    location = builder.location,
                    originalLanguage = builder.originalLanguage,
                    category = builder.category,
                    variants = builder.variants.mapValues { (length, texts) ->
                        PassageVariant(length = length, texts = texts.values.toList())
                    },
                ),
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
