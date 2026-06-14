#!/usr/bin/env bash
set -euo pipefail

# Idempotent: safe to re-run via `grab hook anysite-mcp`.
# Pre-builds the virtualenv so the first `grab exec` is instant.

VENV="${GRAB_TOOL_DIR}/.venv"

if ! command -v python3 >/dev/null 2>&1; then
    echo "  ⚠ python3 not found in PATH — install Python 3.10+ before using anysite-mcp."
    exit 0
fi

if [[ ! -x "${VENV}/bin/python" ]]; then
    echo "  → Creating virtualenv at ${VENV}"
    python3 -m venv "$VENV"
fi

echo "  → Installing dependencies (trafilatura, markdownify)…"
"${VENV}/bin/pip" install --quiet --upgrade pip
"${VENV}/bin/pip" install --quiet -r "${GRAB_TOOL_DIR}/requirements.txt"

cat <<EOF
  → Ready. Crawl a docs site with:
      grab exec anysite-mcp https://docs.example.com --out ./docs_md
EOF
