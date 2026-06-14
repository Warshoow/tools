#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for `grab exec websearchTool <cmd>`.
# Builds and runs the FastAPI web-search service in Docker. It uses DuckDuckGo
# for search and an Ollama model on the host for tool-calling chat.
#
# Usage:
#   grab exec websearchTool up       # build (if needed) + run on :8080  (default)
#   grab exec websearchTool build    # just build the image
#   grab exec websearchTool logs     # follow container logs
#   grab exec websearchTool down     # stop the container

HERE="$(cd "$(dirname "$0")" && pwd)"
IMAGE="websearch-tool"
NAME="websearch-tool"
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
            -e MODEL="${MODEL:-llama3.1:8b}" \
            "$IMAGE" "$@"
        ;;
    logs)
        exec docker logs -f "$NAME"
        ;;
    down|stop)
        exec docker stop "$NAME"
        ;;
    *)
        echo "Unknown command: $cmd (try: up, build, logs, down)" >&2
        exit 1
        ;;
esac
