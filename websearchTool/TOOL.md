Web-search service (FastAPI in Docker): Ollama tool-calling chat backed by DuckDuckGo search.

Exposes an HTTP API on `:8080`. The model decides when to call the `web_search` tool
(DuckDuckGo via `ddgs`) to fetch current information, then answers from the results.
Useful as a tiny local "search-augmented" backend for the orchestrator or your own apps.

## Requirements

- Docker
- Ollama running on the host with a tool-calling model (e.g. `ollama pull llama3.1:8b`)

## Install

```bash
grab add websearchTool
```

## Usage

```bash
grab exec websearchTool up      # build (if needed) + run on :8080
grab exec websearchTool build   # build the image only
grab exec websearchTool logs    # follow logs
grab exec websearchTool down    # stop the container
```

Call it:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the latest stable Node.js LTS version?"}'
```

## Configuration

| Var | Default |
|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` |
| `MODEL` | `llama3.1:8b` |
| `PORT` | `8080` (host port) |

The container is started with `--add-host host.docker.internal:host-gateway` so it can
reach Ollama on the host under Linux as well as Docker Desktop.
