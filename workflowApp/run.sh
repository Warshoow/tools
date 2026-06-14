#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for `grab exec workflowApp <cmd>`.
# Installs deps on first run, then runs the Vite app.
#
# Usage:
#   grab exec workflowApp dev       # start the dev server (default)
#   grab exec workflowApp build     # production build
#   grab exec workflowApp preview   # preview the production build

HERE="$(cd "$(dirname "$0")" && pwd)"

if ! command -v npm >/dev/null 2>&1; then
    echo "✖ npm not found in PATH — install Node.js (>= 20) first." >&2
    exit 1
fi

# Install deps on first run (or after a fresh grab install).
if [[ ! -d "${HERE}/node_modules" ]]; then
    echo "→ Installing dependencies (first run)…" >&2
    ( cd "$HERE" && npm install )
fi

cmd="${1:-dev}"
[[ $# -gt 0 ]] && shift

exec npm --prefix "$HERE" run "$cmd" -- "$@"
