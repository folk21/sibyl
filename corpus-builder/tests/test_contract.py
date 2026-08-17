from pathlib import Path

from sibyl_corpus_builder.build._internal.database import SCHEMA


def test_builder_schema_matches_canonical_contract() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    canonical = (repository_root / "corpus-format" / "schema.sql").read_text(encoding="utf-8")

    assert SCHEMA.strip() == canonical.strip()
