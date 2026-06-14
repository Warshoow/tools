#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for `grab exec anysite-mcp <base_url> [options]`.
# Runs the docs crawler from a self-contained virtualenv next to this script,
# so it never touches the host's global Python packages.

HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="${HERE}/.venv"
PYBIN="${VENV}/bin/python"

if ! command -v python3 >/dev/null 2>&1; then
    echo "✖ python3 not found in PATH — install Python 3.10+ first." >&2
    exit 1
fi

# Lazy bootstrap: build the venv on first run (or after `grab clean`/reinstall).
if [[ ! -x "$PYBIN" ]]; then
    echo "→ Setting up virtualenv (first run)…" >&2
    python3 -m venv "$VENV"
    "${VENV}/bin/pip" install --quiet --upgrade pip
    "${VENV}/bin/pip" install --quiet -r "${HERE}/requirements.txt"
fi

exec "$PYBIN" "${HERE}/main.py" "$@"
