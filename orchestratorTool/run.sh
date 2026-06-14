#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for `grab exec orchestratorTool <cmd>`.
# Builds and runs the FastAPI orchestrator/executor service in Docker.
# It talks to an Ollama instance on the host (default http://host.docker.internal:11434).
#
# Usage:
#   grab exec orchestratorTool up       # build (if needed) + run on :8080  (default)
#   grab exec orchestratorTool build    # just build the image
#   grab exec orchestratorTool test     # POST a sample task to a running instance
#   grab exec orchestratorTool health   # GET /health
#   grab exec orchestratorTool logs     # follow container logs

HERE="$(cd "$(dirname "$0")" && pwd)"
IMAGE="orchestrator-tool"
NAME="orchestrator-tool"
PORT="${PORT:-8080}"

build() {
    echo "→ Building ${IMAGE}…" >&2
    docker build -t "$IMAGE" "$HERE"
}

cmd="${1:-up}"
[[ $# -gt 0 ]] && shift

case "$cmd" in
    build)
        build
        ;;
    up|run)
        docker image inspect "$IMAGE" >/dev/null 2>&1 || build
        echo "→ http://localhost:${PORT}  (Ollama must be running: ollama serve)" >&2
        exec docker run --rm -it --name "$NAME" \
            -p "${PORT}:8080" \
            --add-host host.docker.internal:host-gateway \
            -e OLLAMA_HOST="${OLLAMA_HOST:-http://host.docker.internal:11434}" \
            "$IMAGE" "$@"
        ;;
    logs)
        exec docker logs -f "$NAME"
        ;;
    health)
        exec curl -fsS "http://localhost:${PORT}/health"
        ;;
    test)
        exec curl -fsS -X POST "http://localhost:${PORT}/orchestrate" \
            -H "Content-Type: application/json" \
            -d '{"task": "What is 25 * 4?"}'
        ;;
    down|stop)
        exec docker stop "$NAME"
        ;;
    *)
        echo "Unknown command: $cmd (try: up, build, logs, health, test, down)" >&2
        exit 1
        ;;
esac
