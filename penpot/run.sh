#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for `grab exec penpot <cmd>`.
# Always operates against the docker-compose.yml shipped alongside this script,
# regardless of where it is invoked from.

HERE="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${HERE}/docker-compose.yml"
ENV_FILE="${HERE}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "✖ ${ENV_FILE} not found. Run: grab hook penpot" >&2
    exit 1
fi

COMPOSE=(docker compose --project-directory "$HERE" -f "$COMPOSE_FILE" --env-file "$ENV_FILE")

cmd="${1:-up}"
[[ $# -gt 0 ]] && shift

case "$cmd" in
    up)
        "${COMPOSE[@]}" up -d "$@"
        echo "→ http://localhost:9001  (mailcatch: http://localhost:1080)"
        ;;
    down)
        "${COMPOSE[@]}" down "$@"
        ;;
    restart)
        "${COMPOSE[@]}" restart "$@"
        ;;
    logs)
        "${COMPOSE[@]}" logs -f "$@"
        ;;
    status|ps)
        "${COMPOSE[@]}" ps
        ;;
    pull)
        "${COMPOSE[@]}" pull
        ;;
    *)
        # Passthrough to docker compose for anything else (exec, run, config, ...)
        "${COMPOSE[@]}" "$cmd" "$@"
        ;;
esac
