Bidirectional Ollama orchestrator/executor API (FastAPI in Docker) — two local LLMs plan and execute tasks with tools.

An **Orchestrator** model plans and evaluates while an **Executor** model runs sub-tasks
(with tool access) and can ask clarifying questions. Exposes an HTTP API on `:8080`.
Full design notes live in `README.md` and `CODING_MODELS.md`.

## Requirements

- Docker
- Ollama running on the host with at least one model pulled (e.g. `ollama pull llama3.1:8b`)

## Install

```bash
grab add orchestratorTool
```

## Usage

```bash
grab exec orchestratorTool up        # build (if needed) + run on :8080
grab exec orchestratorTool build     # build the image only
grab exec orchestratorTool health    # GET /health
grab exec orchestratorTool test      # POST a sample task
grab exec orchestratorTool logs      # follow logs
grab exec orchestratorTool down      # stop the container
```

Call it directly:

```bash
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Search for the current Bitcoin price and calculate 0.5 BTC"}'
```

## Configuration

Override at exec time via environment variables (passed through to the container):

| Var | Default |
|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` |
| `ORCHESTRATOR_MODEL` | `llama3.1:8b` |
| `EXECUTOR_MODEL` | `llama3.1:8b` |
| `PORT` | `8080` (host port) |

```bash
OLLAMA_HOST=http://host.docker.internal:11434 grab exec orchestratorTool up
```

The container is started with `--add-host host.docker.internal:host-gateway` so it can
reach Ollama on the host under Linux as well as Docker Desktop.
