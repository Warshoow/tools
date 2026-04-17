#!/usr/bin/env bash
set -euo pipefail

# Idempotent: safe to re-run via `grab hook penpot`.

ENV_FILE="${GRAB_TOOL_DIR}/.env"
ENV_EXAMPLE="${GRAB_TOOL_DIR}/.env.example"

# 1. Seed .env from .env.example on first install (don't clobber user edits)
if [[ ! -f "$ENV_FILE" && -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "  → Created ${ENV_FILE}"
fi

# 2. Generate PENPOT_SECRET_KEY if still empty
if [[ -f "$ENV_FILE" ]] && grep -q '^PENPOT_SECRET_KEY=$' "$ENV_FILE"; then
    KEY=""
    if command -v python3 >/dev/null 2>&1; then
        KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    elif command -v openssl >/dev/null 2>&1; then
        KEY=$(openssl rand -base64 64 | tr -d '\n')
    else
        echo "  ⚠ Neither python3 nor openssl found — generate PENPOT_SECRET_KEY manually in ${ENV_FILE}"
    fi

    if [[ -n "$KEY" ]]; then
        # Portable in-place edit (works on GNU and BSD sed). Use a delimiter
        # unlikely to appear in a base64 url-safe string.
        sed -i.bak "s|^PENPOT_SECRET_KEY=$|PENPOT_SECRET_KEY=${KEY}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
        echo "  → Generated PENPOT_SECRET_KEY"
    fi
fi

# 3. Sanity-check docker availability
if ! command -v docker >/dev/null 2>&1; then
    echo "  ⚠ docker not found in PATH — install Docker Desktop / Docker Engine before launching"
    exit 0
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "  ⚠ 'docker compose' subcommand not available — upgrade Docker or install the compose plugin"
    exit 0
fi

cat <<EOF
  → Ready. Launch with:
      grab exec penpot up
    Then open http://localhost:9001
EOF
