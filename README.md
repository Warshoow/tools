# tools

Personal monorepo of shareable tools, designed to be cherry-picked into any project with
[`grab`](https://github.com/Warshoow/grab).

Each tool lives in its own top-level directory and follows the grab layout:

| File | Role |
|---|---|
| `TOOL.md` | Docs. Its **first line** is the description shown by `grab list --remote`. |
| `run.sh` | Entrypoint for `grab exec <tool> [args]` (optional). |
| `post-grab.sh` | Setup hook run after install — seeds config, builds venvs, copies files (optional). |

## Quick start

```bash
# One-time, in a project:
grab init git@github.com:Warshoow/tools.git

# Pull a tool (--hook runs its post-grab.sh setup):
grab add penpot --hook

# Run it:
grab exec penpot up

# Discover what's available:
grab list --remote
```

## Tools

| Tool | What it does | `grab exec` | Hook |
|---|---|---|---|
| **dbc** | Docker-compose DB CLI — auto-detects credentials, opens a shell or runs queries | ✅ | — |
| **penpot** | Self-hosted Penpot (Figma alternative) via docker compose | ✅ | ✅ |
| **anysite-mcp** | Crawl a website's docs into clean `.md` for grepai/ripgrep | ✅ | ✅ |
| **stripe-cli** | Stripe CLI (webhook listener + event triggers) via Docker | ✅ | ✅ |
| **orchestratorTool** | Ollama orchestrator/executor API (FastAPI in Docker) | ✅ | — |
| **websearchTool** | Ollama + DuckDuckGo tool-calling search API (FastAPI in Docker) | ✅ | — |
| **workflowApp** | "Local AI Workflows" — Vue 3 + Vite node-based builder (scaffold) | ✅ | — |
| **github-commit** | React component: list your GitHub commits across repos in a date range | ✅ (Vite preview) | — |
| **devcontainer** | Drop a ready-to-use VSCode devcontainer into a project | — | ✅ |

See each tool's `TOOL.md` for full usage.

## Conventions for new tools

- For `grab exec` to find an entrypoint, the tool must contain one of:
  `run.sh`, `main.sh`, `<tool>.sh`, or `entrypoint.sh`.
- `run.sh` should resolve its own directory (`HERE="$(cd "$(dirname "$0")" && pwd)"`) and
  operate relative to it, so it works regardless of the caller's CWD.
- `post-grab.sh` must be **idempotent** (it can be re-run with `grab hook <tool>`) and can
  use these env vars: `GRAB_TOOL_NAME`, `GRAB_TOOL_DIR`, `GRAB_PROJECT_DIR`.
- Keep secrets out of git: ship a `.env.example`, seed the real `.env` in `post-grab.sh`.
  Installed tools live under the gitignored `.grab/tools/`, so per-machine state
  (`.venv/`, `node_modules/`, `.env`) stays out of consuming projects.

## Publishing

From a standalone dev folder, publish it into this monorepo:

```bash
grab publish ~/dev/my-new-tool
```
