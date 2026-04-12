#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${GRAB_PROJECT_DIR}/.devcontainer"

if [[ -d "$TARGET_DIR" ]]; then
    echo "  .devcontainer/ already exists in project root, overwrite? [y/N]"
    read -r confirm
    [[ "$confirm" != [yY] ]] && echo "  Skipped." && exit 0
    rm -rf "$TARGET_DIR"
fi

mkdir -p "$TARGET_DIR"
cp "${GRAB_TOOL_DIR}/devcontainer.json" "$TARGET_DIR/devcontainer.json"
cp "${GRAB_TOOL_DIR}/Dockerfile.dev"    "$GRAB_PROJECT_DIR/Dockerfile.dev"
cp "${GRAB_TOOL_DIR}/docker-compose.dev.yml" "$GRAB_PROJECT_DIR/docker-compose.dev.yml"
cp "${GRAB_TOOL_DIR}/setup-dev.sh"      "$TARGET_DIR/setup-dev.sh"
chmod +x "$TARGET_DIR/setup-dev.sh"

echo "  Installed .devcontainer/ to project root"