import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _insert_base_fixture(connection: sqlite3.Connection) -> None:
    connection.execute("INSERT INTO author(id, display_name) VALUES ('a', 'Fixture')")
    connection.execute(
        "INSERT INTO work(id, author_id, title, original_language, category) "
        "VALUES ('w', 'a', 'Work', 'en', 'literature')"
    )
    connection.execute(
        "INSERT INTO text_version(id, work_id, language, role, source_name) "
        "VALUES ('tv', 'w', 'en', 'original', 'fixture')"
    )
    connection.execute(
        "INSERT INTO passage(id, work_id, ordinal, source_locator) "
        "VALUES ('p', 'w', 0, 'ordinal:0')"
    )
    connection.execute(
        "INSERT INTO passage_text(passage_id, text_version_id, variant, text, word_count) "
        "VALUES ('p', 'tv', 'short', 'fixture text', 2)"
    )
    connection.execute(
        "INSERT INTO semantic_hint(id, passage_id, text) VALUES ('h', 'p', 'fixture hint')"
    )
    connection.execute(
        "INSERT INTO guided_question_catalog(id, language) VALUES ('catalog', 'en')"
    )
    connection.execute(
        "INSERT INTO guided_question(id, catalog_id, ordinal, kind, theme, text) "
        "VALUES ('q', 'catalog', 0, 'question', 'fixture', 'Fixture question?')"
    )
    connection.execute(
        "INSERT INTO guided_question_passage(question_id, passage_id, strength) "
        "VALUES ('q', 'p', 0.75)"
    )


def _expect_integrity_error(connection: sqlite3.Connection, sql: str) -> None:
    try:
        connection.execute(sql)
    except sqlite3.IntegrityError:
        return
    raise SystemExit(f"Expected SQLite integrity error for: {sql}")


def validate_sql_schema() -> None:
    """Executes the canonical SQL schema and verifies its required relational contract."""
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8")
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        required = {
            "metadata",
            "author",
            "work",
            "text_version",
            "passage",
            "passage_text",
            "semantic_hint",
            "guided_question_catalog",
            "guided_question",
            "guided_question_passage",
        }
        missing = required - tables
        if missing:
            raise SystemExit(f"Missing required tables: {sorted(missing)}")

        _insert_base_fixture(connection)
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise SystemExit(f"Foreign key violations: {violations}")

        _expect_integrity_error(
            connection,
            "INSERT INTO guided_question_passage(question_id, passage_id, strength) "
            "VALUES ('q', 'p', 0.5)",
        )
        _expect_integrity_error(
            connection,
            "INSERT INTO guided_question_passage(question_id, passage_id, strength) "
            "VALUES ('q', 'missing', 0.5)",
        )
        _expect_integrity_error(
            connection,
            "INSERT INTO guided_question_passage(question_id, passage_id, strength) "
            "VALUES ('missing', 'p', 0.5)",
        )
        connection.execute(
            "INSERT INTO passage(id, work_id, ordinal, source_locator) "
            "VALUES ('p2', 'w', 1, 'ordinal:1')"
        )
        _expect_integrity_error(
            connection,
            "INSERT INTO guided_question_passage(question_id, passage_id, strength) "
            "VALUES ('q', 'p2', 1.1)",
        )


def validate_manifest_schema_document() -> None:
    """Checks manifest schema requirements and VERSION consistency."""
    document = json.loads((ROOT / "manifest.schema.json").read_text(encoding="utf-8"))
    required = set(document.get("required", []))
    expected = {"format_version", "language", "embedding", "counts", "artifacts"}
    missing = expected - required
    if missing:
        raise SystemExit(f"Manifest schema does not require fields: {sorted(missing)}")

    count_required = set(document["properties"]["counts"].get("required", []))
    guided_counts = {"guided_questions", "guided_mappings"}
    if missing_counts := guided_counts - count_required:
        raise SystemExit(f"Manifest counts do not require fields: {sorted(missing_counts)}")

    format_version = document.get("properties", {}).get("format_version", {}).get("const")
    version = int((ROOT / "VERSION").read_text(encoding="utf-8").strip())
    if format_version != version:
        raise SystemExit(
            f"Manifest schema format version {format_version!r} does not match VERSION {version}"
        )


def validate_schema() -> None:
    """Runs all corpus-format self-validation checks."""
    validate_sql_schema()
    validate_manifest_schema_document()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    print(f"Corpus format schema v{version} is valid.")


if __name__ == "__main__":
    validate_schema()
