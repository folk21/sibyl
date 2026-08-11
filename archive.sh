#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_name="$(basename "$repo_dir")"
parent_dir="$(dirname "$repo_dir")"
archive_path="${1:-$parent_dir/archive_sibyl.zip}"

if [[ "$repo_name" != "sibyl" ]]; then
  echo "Expected repository directory name 'sibyl', got '$repo_name'." >&2
  echo "Rename the checkout to 'sibyl' before creating a shareable archive." >&2
  exit 2
fi

rm -f "$archive_path"
cd "$parent_dir"

zip -r "$archive_path" "$repo_name" \
  -x "*/.idea/*" \
     "*/.git/*" \
     "*/.venv/*" \
     "*/.kotlin/*" \
     "*/.gradle/*" \
     "*/.gradle-dist/*" \
     "*/build/*" \
     "*/target/*" \
     "*/__pycache__/*" \
     "*/.pytest_cache/*" \
     "*/.mypy_cache/*" \
     "*/.ruff_cache/*" \
     "*/*.egg-info/*" \
     "*/node_modules/*" \
     "*/.DS_Store" \
     "*/local.properties" \
     "*.class" \
     "*.pyc" \
     "*.pyo" \
     "*.zip"

echo "Created $archive_path"
