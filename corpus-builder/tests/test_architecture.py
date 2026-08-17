"""Regression guards for the Python corpus package dependency direction."""

import ast
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_BUILDER_PACKAGE = _REPOSITORY_ROOT / "corpus-builder" / "src" / "sibyl_corpus_builder"
_CORE_PACKAGE = _REPOSITORY_ROOT / "corpus-core" / "src" / "sibyl_corpus_core"
_FEATURES = {"sources", "build", "curation"}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = "." * node.level + module
            result.append(module)
    return result


def test_corpus_core_does_not_depend_on_builder() -> None:
    violations = []
    for path in _CORE_PACKAGE.rglob("*.py"):
        for imported in _imports(path):
            if "sibyl_corpus_builder" in imported:
                violations.append(f"{path.relative_to(_REPOSITORY_ROOT)} -> {imported}")
    assert violations == []


def test_root_cli_only_composes_feature_command_modules() -> None:
    imports = _imports(_BUILDER_PACKAGE / "cli.py")
    assert all("_internal" not in imported for imported in imports)
    assert all("adapters" not in imported for imported in imports)


def test_features_do_not_import_other_feature_internals() -> None:
    violations = []
    for feature in _FEATURES:
        feature_root = _BUILDER_PACKAGE / feature
        for path in feature_root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for other in _FEATURES - {feature}:
                forbidden = f"sibyl_corpus_builder.{other}._internal"
                if forbidden in source:
                    violations.append(f"{path.relative_to(_REPOSITORY_ROOT)} -> {forbidden}")
                # Relative imports are also forbidden when they explicitly cross to another feature.
                if f"..{other}._internal" in source or f"...{other}._internal" in source:
                    violations.append(
                        f"{path.relative_to(_REPOSITORY_ROOT)} -> relative {other}._internal"
                    )
    assert violations == []

def test_python_packages_have_meaningful_package_docstrings() -> None:
    package_roots = (_CORE_PACKAGE, _BUILDER_PACKAGE)
    violations = []
    for package_root in package_roots:
        for init_path in package_root.rglob("__init__.py"):
            tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
            docstring = ast.get_docstring(tree, clean=True) or ""
            if len(docstring) < 120 or docstring.strip() == "Internal package.":
                violations.append(str(init_path.relative_to(_REPOSITORY_ROOT)))
    assert violations == []

