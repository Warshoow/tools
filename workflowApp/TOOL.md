Local AI Workflows — Vue 3 + Vite (Tauri-targeted) node-based builder for chaining local Ollama models.

A desktop-oriented app to build and run visual workflows between local AI models (via
Ollama), fully offline after install. Node-based canvas (Vue Flow), a simple chat tab,
and an integrated code editor are the planned surface — see `idea.md` and
`project-plan.md` for the full vision.

> Status: scaffold (Vue 3 + TypeScript + Vite). The Tauri shell and Vue Flow canvas
> described in `idea.md` are not wired up yet.

## Requirements

- Node.js >= 20 (for npm)

## Install

```bash
grab add workflowApp
```

## Usage

```bash
grab exec workflowApp dev        # start the Vite dev server (default)
grab exec workflowApp build      # production build (vue-tsc + vite build)
grab exec workflowApp preview    # preview the built app
```

`dev` prints a local URL (default http://localhost:5173). `node_modules` is installed
automatically on first run and lives under `.grab/tools/`, out of your project's git.
