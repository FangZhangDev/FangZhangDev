#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
"${PYTHON_BIN}" profile.py update --config config.toml

# dist/*.html 已在 .gitignore 中排除，这里可以整目录 add
git add data/daily.jsonl dist README.md docs
if git diff --cached --quiet; then
  echo "No profile changes to publish."
  exit 0
fi

git commit -m "chore: update coding activity profile"
git push
