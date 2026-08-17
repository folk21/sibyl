#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_name="$(basename "$repo_dir")"
parent_dir="$(dirname "$repo_dir")"
concat_tool="${SIBYL_CONCAT_TOOL:-$HOME/work/python/concat_files_to_txt.py}"
output_path="${1:-$parent_dir/sibyl_files.txt}"
python_bin="${PYTHON:-python3}"

if [[ "$repo_name" != "sibyl" ]]; then
  echo "Expected repository directory name 'sibyl', got '$repo_name'." >&2
  exit 2
fi

if [[ ! -f "$concat_tool" ]]; then
  echo "Concat tool not found: $concat_tool" >&2
  echo "Set SIBYL_CONCAT_TOOL to the path of concat_files_to_txt.py." >&2
  exit 2
fi

"$python_bin" "$concat_tool" \
  "$repo_dir" \
  "$output_path" \
  -i .git -i .idea -i .vscode \
  -i __pycache__ -i '*/__pycache__/*' \
  -i .pytest_cache -i '*/.pytest_cache/*' \
  -i .mypy_cache -i .ruff_cache \
  -i .gradle -i '*/.gradle/*' \
  -i .gradle-dist -i '*/.gradle-dist/*' \
  -i .kotlin -i '*/.kotlin/*' \
  -i 'mobile/build/*' -i 'mobile/*/build/*' \
  -i 'corpus-core/build/*' -i 'corpus-builder/build/*' \
  -i target -i '*/target/*' \
  -i dist -i '*/dist/*' \
  -i '*.egg-info' -i '*/*.egg-info/*' \
  -i .venv -i .venv-ml -i venv -i env -i 'env*' \
  -i '*/.venv/*' -i '*/.venv-ml/*' \
  -i .cache -i '*/.cache/*' \
  -i .huggingface -i '*/.huggingface/*' \
  -i .torch -i '*/.torch/*' \
  -i node_modules -i '*/node_modules/*' \
  -i corpus-builder/data -i '*/corpus-builder/data/*' \
  -i local.properties -i sibyl_files.txt \
  -e .kt -e .kts -e .py -e .md -e .txt \
  -e .ini -e .toml -e .yaml -e .yml -e .json \
  -e .sh -e .gitignore -e .properties -e .sql -e .xml \
  -e .editorconfig -e Makefile -e VERSION

required_source="sibyl_corpus_builder/build/api.py"
if ! grep -Fq "$required_source" "$output_path"; then
  rm -f "$output_path"
  echo "Snapshot validation failed: required source package entry is missing: $required_source" >&2
  exit 2
fi

echo "Created $output_path"
