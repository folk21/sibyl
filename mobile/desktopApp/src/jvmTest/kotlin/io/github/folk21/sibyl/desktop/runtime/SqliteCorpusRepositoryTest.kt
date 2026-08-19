package io.github.folk21.sibyl.desktop.runtime

import java.nio.file.Files
import java.nio.file.Path
import java.sql.DriverManager
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.coroutines.runBlocking

/** Verifies Desktop guided SQLite lookup exposes only mapped questions and exact stored passage text. */
class SqliteCorpusRepositoryTest {
    @Test
    fun `format four exposes mapped questions in catalog order and strength ranked candidates`() = runBlocking {
        val database = createFixtureDatabase()
        try {
            SqliteCorpusRepository(database, formatVersion = 4).use { repository ->
                assertEquals(
                    listOf("question-a", "question-c"),
                    repository.availableQuestions().map { it.id },
                )

                val candidates = repository.candidates("question-a", limit = 10)
                assertEquals(listOf("p-strong", "p-low"), candidates.map { it.passage.id })
                assertEquals(listOf(0.9, 0.1), candidates.map { it.semanticScore })
                val strongTexts = candidates[0].passage.variants.values.single().texts
                assertEquals(
                    "Exact strong stored text.",
                    strongTexts.first { it.language == "en" }.text,
                )
                assertEquals(
                    "Сохранённый машинный перевод.",
                    strongTexts.first { it.language == "ru" }.text,
                )
                assertEquals(
                    "fixture-provider",
                    strongTexts.first { it.language == "ru" }.translationProvider,
                )
                assertEquals(
                    "Exact low stored text.",
                    candidates[1].passage.variants.values.single().texts.single().text,
                )
                assertEquals(emptyList(), repository.candidates("missing", limit = 10))
            }
        } finally {
            Files.deleteIfExists(database)
        }
    }

    @Test
    fun `format three does not query guided tables`() = runBlocking {
        val database = Files.createTempFile("sibyl-v3-", ".db")
        try {
            DriverManager.getConnection("jdbc:sqlite:${database.toAbsolutePath()}").use { connection ->
                connection.createStatement().use { statement ->
                    statement.execute("CREATE TABLE semantic_hint(id TEXT PRIMARY KEY, passage_id TEXT, text TEXT)")
                }
            }
            SqliteCorpusRepository(database, formatVersion = 3).use { repository ->
                assertEquals(emptyList(), repository.availableQuestions())
                assertEquals(emptyList(), repository.candidates("question-a", limit = 10))
            }
        } finally {
            Files.deleteIfExists(database)
        }
    }

    private fun createFixtureDatabase(): Path {
        val database = Files.createTempFile("sibyl-guided-", ".db")
        DriverManager.getConnection("jdbc:sqlite:${database.toAbsolutePath()}").use { connection ->
            connection.createStatement().use { statement ->
                statement.executeUpdate("CREATE TABLE author(id TEXT PRIMARY KEY, display_name TEXT NOT NULL)")
                statement.executeUpdate(
                    "CREATE TABLE work(id TEXT PRIMARY KEY, author_id TEXT NOT NULL, title TEXT NOT NULL, " +
                        "original_language TEXT NOT NULL, category TEXT NOT NULL)",
                )
                statement.executeUpdate(
                    "CREATE TABLE text_version(id TEXT PRIMARY KEY, work_id TEXT NOT NULL, language TEXT NOT NULL, " +
                        "role TEXT NOT NULL, translator TEXT, translation_provider TEXT, translation_model TEXT)",
                )
                statement.executeUpdate(
                    "CREATE TABLE passage(id TEXT PRIMARY KEY, work_id TEXT NOT NULL, ordinal INTEGER NOT NULL, " +
                        "source_locator TEXT NOT NULL, quality_score REAL)",
                )
                statement.executeUpdate(
                    "CREATE TABLE passage_text(passage_id TEXT NOT NULL, text_version_id TEXT NOT NULL, " +
                        "variant TEXT NOT NULL, text TEXT NOT NULL)",
                )
                statement.executeUpdate(
                    "CREATE TABLE semantic_hint(id TEXT PRIMARY KEY, passage_id TEXT NOT NULL, text TEXT NOT NULL)",
                )
                statement.executeUpdate(
                    "CREATE TABLE guided_question_catalog(id TEXT PRIMARY KEY, language TEXT NOT NULL)",
                )
                statement.executeUpdate(
                    "CREATE TABLE guided_question(id TEXT PRIMARY KEY, catalog_id TEXT NOT NULL, ordinal INTEGER NOT NULL, " +
                        "kind TEXT NOT NULL, theme TEXT NOT NULL, text TEXT NOT NULL)",
                )
                statement.executeUpdate(
                    "CREATE TABLE guided_question_passage(question_id TEXT NOT NULL, passage_id TEXT NOT NULL, " +
                        "strength REAL NOT NULL)",
                )
                statement.executeUpdate("INSERT INTO author VALUES ('author', 'Fixture Author')")
                statement.executeUpdate("INSERT INTO work VALUES ('work', 'author', 'Fixture Work', 'en', 'literature')")
                statement.executeUpdate(
                    "INSERT INTO text_version VALUES " +
                        "('tv', 'work', 'en', 'original', NULL, NULL, NULL)",
                )
                statement.executeUpdate(
                    "INSERT INTO text_version VALUES ('tv-ru', 'work', 'ru', 'machine_translation', NULL, " +
                        "'fixture-provider', 'fixture-model')",
                )
                statement.executeUpdate(
                    "INSERT INTO passage VALUES ('p-strong', 'work', 0, 'chars:0:24', NULL)",
                )
                statement.executeUpdate(
                    "INSERT INTO passage VALUES ('p-low', 'work', 1, 'chars:25:47', NULL)",
                )
                statement.executeUpdate(
                    "INSERT INTO passage_text VALUES " +
                        "('p-strong', 'tv', 'standard', 'Exact strong stored text.')",
                )
                statement.executeUpdate(
                    "INSERT INTO passage_text VALUES ('p-strong', 'tv-ru', 'standard', 'Сохранённый машинный перевод.')",
                )
                statement.executeUpdate(
                    "INSERT INTO passage_text VALUES " +
                        "('p-low', 'tv', 'standard', 'Exact low stored text.')",
                )
                statement.executeUpdate("INSERT INTO guided_question_catalog VALUES ('catalog', 'en')")
                statement.executeUpdate("INSERT INTO guided_question VALUES ('question-a', 'catalog', 0, 'question', 'change', 'Question A?')")
                statement.executeUpdate("INSERT INTO guided_question VALUES ('question-b', 'catalog', 1, 'question', 'change', 'Question B?')")
                statement.executeUpdate("INSERT INTO guided_question VALUES ('question-c', 'catalog', 2, 'state', 'doubt', 'Question C')")
                statement.executeUpdate("INSERT INTO guided_question_passage VALUES ('question-a', 'p-low', 0.1)")
                statement.executeUpdate("INSERT INTO guided_question_passage VALUES ('question-a', 'p-strong', 0.9)")
                statement.executeUpdate("INSERT INTO guided_question_passage VALUES ('question-c', 'p-low', 0.5)")
            }
        }
        return database
    }
}
