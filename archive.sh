#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_name="$(basename "$repo_dir")"
parent_dir="$(dirname "$repo_dir")"
archive_path="${1:-$parent_dir/sibyl-FULL.zip}"

if [[ "$repo_name" != "sibyl" ]]; then
  echo "Expected repository directory name 'sibyl', got '$repo_name'." >&2
  echo "Rename the checkout to 'sibyl' before creating a shareable archive." >&2
  exit 2
fi

rm -f "$archive_path"
cd "$parent_dir"

zip -r "$archive_path" "$repo_name" \
  -x "*/.idea/*" \
     "*/.vscode/*" \
     "*/.git/*" \
     "*/.venv*/*" \
     "*/.kotlin/*" \
     "*/.gradle/*" \
     "*/.gradle-dist/*" \
     "sibyl/build/*" \
     "sibyl/mobile/build/*" \
     "sibyl/mobile/*/build/*" \
     "sibyl/corpus-core/build/*" \
     "sibyl/corpus-builder/build/*" \
     "*/target/*" \
     "*/dist/*" \
     "*/__pycache__/*" \
     "*/.pytest_cache/*" \
     "*/.mypy_cache/*" \
     "*/.ruff_cache/*" \
     "*/.cache/*" \
     "*/.huggingface/*" \
     "*/.torch/*" \
     "*/*.egg-info/*" \
     "*/node_modules/*" \
     "*/corpus-builder/data/*" \
     "*/.DS_Store" \
     "*/local.properties" \
     "*/sibyl_files.txt" \
     "*.class" \
     "*.pyc" \
     "*.pyo" \
     "*.onnx" \
     "*.safetensors" \
     "*.gguf" \
     "*.usearch" \
     "*.zip"

required_source="$repo_name/corpus-builder/src/sibyl_corpus_builder/build/api.py"
archive_listing="$(unzip -Z1 "$archive_path")"
if ! grep -Fxq "$required_source" <<<"$archive_listing"; then
  rm -f "$archive_path"
  echo "Archive validation failed: required source package entry is missing: $required_source" >&2
  exit 2
fi

echo "Created $archive_path"
