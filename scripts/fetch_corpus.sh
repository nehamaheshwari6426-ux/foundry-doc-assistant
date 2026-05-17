#!/usr/bin/env bash
# Fetch the Foundry doc subset from MicrosoftDocs/azure-ai-docs using a
# sparse-checkout. Idempotent — safe to re-run; will pull updates if the
# checkout already exists.
#
# Output: ./corpus/source/ — markdown files as authored upstream.

set -euo pipefail

REPO_URL="https://github.com/MicrosoftDocs/azure-ai-docs.git"
TARGET_DIR="corpus/source"
PATHS=(
  "articles/foundry"
)

if [[ -d "${TARGET_DIR}/.git" ]]; then
  echo "Updating existing checkout in ${TARGET_DIR}..."
  ( cd "${TARGET_DIR}" && git pull --depth 1 origin main )
else
  echo "Cloning ${REPO_URL} (sparse) into ${TARGET_DIR}..."
  git clone --depth 1 --filter=blob:none --sparse "${REPO_URL}" "${TARGET_DIR}"
  ( cd "${TARGET_DIR}" && git sparse-checkout set "${PATHS[@]}" )
fi

echo
echo "Markdown file count under sparse paths:"
find "${TARGET_DIR}" -name "*.md" -not -path "*/.git/*" | wc -l