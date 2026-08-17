"""Regression guards for repository helpers that package or concatenate source code."""

from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_BUILD_FEATURE = "corpus-builder/src/sibyl_corpus_builder/build/api.py"


def test_build_feature_is_present_in_source_tree() -> None:
    """The automatic-build feature is source code, not a generated build-output directory."""
    assert (_REPOSITORY_ROOT / _BUILD_FEATURE).is_file()


def test_gitignore_does_not_globally_ignore_build_directories() -> None:
    """Git must track the Python build feature while ignoring only known generated outputs."""
    gitignore = (_REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
    rules = {line.strip() for line in gitignore.splitlines()}

    assert "**/build/" not in rules
    assert "/mobile/**/build/" in rules
    assert "corpus-builder/build/" in rules
    assert "corpus-core/build/" in rules


def test_archive_helper_does_not_globally_exclude_build_directories() -> None:
    """A generic */build/* exclusion would silently remove the Python build feature."""
    script = (_REPOSITORY_ROOT / "archive.sh").read_text(encoding="utf-8")

    assert '"*/build/*"' not in script
    assert "required_source=" in script
    assert "sibyl_corpus_builder/build/api.py" in script


def test_concat_helper_does_not_globally_exclude_build_directories() -> None:
    """Source snapshots must retain the Python build feature while ignoring known outputs."""
    script = (_REPOSITORY_ROOT / "concat_sibyl.sh").read_text(encoding="utf-8")

    assert "-i build " not in script
    assert "-i '*/build/*'" not in script
    assert "required_source=" in script
    assert "sibyl_corpus_builder/build/api.py" in script
