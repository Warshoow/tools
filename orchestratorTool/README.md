# Orchestrator/Executor Tool

Bidirectional AI interaction tool using Ollama. Two AIs collaborate:
- **Orchestrator**: Plans tasks, coordinates, evaluates results
- **Executor**: Executes sub-tasks using tools, can ask clarifying questions

## Requirements

- Docker
- Ollama running locally with at least one model (e.g., `llama3.1:8b`)

## Quick Start

### 1. Make sure Ollama is running

```bash
ollama serve
```

### 2. Pull a model (if not already done)

```bash
ollama pull llama3.1:8b
```

### 3. Build and run

```bash
cd orchestratorTool
docker build -t orchestrator .
docker run --rm -p 8080:8080 orchestrator
```

## Testing

### Basic test

```bash
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "What is 25 * 4?"}'
```

### Test with web search

```bash
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Search for the current Bitcoin price and calculate what 0.5 BTC is worth"}'
```

### Health check

```bash
curl http://localhost:8080/health
```

### List available tools

```bash
curl http://localhost:8080/tools
```

## Configuration

Environment variables (set with `-e` flag in docker run):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama server URL |
| `ORCHESTRATOR_MODEL` | `llama3.1:8b` | Model for planning/coordination |
| `EXECUTOR_MODEL` | `llama3.1:8b` | Model for task execution |
| `MAX_ITERATIONS` | `20` | Max orchestration loop iterations |
| `MAX_CLARIFICATIONS` | `5` | Max clarification exchanges |

### Example with different models

```bash
docker run --rm -p 8080:8080 \
  -e ORCHESTRATOR_MODEL=llama3.1:70b \
  -e EXECUTOR_MODEL=llama3.1:8b \
  orchestrator
```

## API

### POST /orchestrate

Main endpoint for task orchestration.

**Request:**
```json
{
  "task": "Your task description",
  "orchestrator_model": "llama3.1:8b",
  "executor_model": "llama3.1:8b",
  "max_iterations": 20,
  "include_conversation_history": true
}
```

**Response:**
```json
{
  "success": true,
  "final_result": "Task result...",
  "total_iterations": 3,
  "clarifications_made": 0,
  "tasks_completed": 2,
  "tasks_failed": 0,
  "conversation_history": [...]
}
```

## Executor Tools

### General Tools
- `web_search` - Search the web via DuckDuckGo
- `calculate` - Evaluate math expressions
- `format_json` - Format/validate JSON

### Coding Tools
- `read_file` - Read file contents
- `write_file` - Write/create files
- `list_files` - List directory contents
- `run_command` - Run shell commands (pytest, npm, etc.)
- `search_in_files` - Search for patterns in code

### Example Coding Tasks

```bash
# Read and analyze code
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Read main.py and explain what it does"}'

# Run tests
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Run pytest and fix any failing tests"}'

# Search codebase
curl -X POST http://localhost:8080/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Find all functions that use the database connection"}'
```

Add more tools in `tools.py`.
