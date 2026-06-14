#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for `grab exec github-commit`.
# main.jsx is a single self-contained React component. This script wraps it in a
# throwaway Vite + React harness (under .preview/) and serves it, so you can use the
# commit viewer locally without pasting it into an artifact/sandbox.
#
# Usage:
#   grab exec github-commit          # build harness (first run) + serve
#   grab exec github-commit build    # production build into .preview/dist

HERE="$(cd "$(dirname "$0")" && pwd)"
PREVIEW="${HERE}/.preview"

if ! command -v npm >/dev/null 2>&1; then
    echo "✖ npm not found in PATH — install Node.js (>= 20) first." >&2
    exit 1
fi

# Scaffold the harness once.
if [[ ! -f "${PREVIEW}/package.json" ]]; then
    echo "→ Scaffolding Vite + React preview (first run)…" >&2
    mkdir -p "${PREVIEW}/src"

    cat > "${PREVIEW}/package.json" <<'JSON'
{
  "name": "github-commit-preview",
  "private": true,
  "type": "module",
  "scripts": { "dev": "vite", "build": "vite build", "preview": "vite preview" },
  "dependencies": { "react": "^18.3.1", "react-dom": "^18.3.1" },
  "devDependencies": { "@vitejs/plugin-react": "^4.3.4", "vite": "^5.4.11" }
}
JSON

    cat > "${PREVIEW}/vite.config.js" <<'JS'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({ plugins: [react()] });
JS

    cat > "${PREVIEW}/index.html" <<'HTML'
<!doctype html>
<html lang="fr">
  <head><meta charset="utf-8" /><title>GitHub Commit Viewer</title></head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
HTML

    cat > "${PREVIEW}/src/main.jsx" <<'JS'
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
createRoot(document.getElementById("root")).render(<App />);
JS
fi

# Always re-sync the component so edits to main.jsx show up.
cp "${HERE}/main.jsx" "${PREVIEW}/src/App.jsx"

if [[ ! -d "${PREVIEW}/node_modules" ]]; then
    echo "→ Installing preview dependencies…" >&2
    ( cd "$PREVIEW" && npm install )
fi

cmd="${1:-dev}"
[[ $# -gt 0 ]] && shift
exec npm --prefix "$PREVIEW" run "$cmd" -- "$@"
