#!/usr/bin/env sh
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/portainer_exec.py" "$@"
