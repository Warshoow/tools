#!/usr/bin/env bash
set -euo pipefail

# Idempotent: safe to re-run via `grab hook stripe-cli`.

ENV_FILE="${GRAB_TOOL_DIR}/.env.stripe"
ENV_EXAMPLE="${GRAB_TOOL_DIR}/.env.stripe.example"

# Seed .env.stripe on first install (never clobber an existing one).
if [[ ! -f "$ENV_FILE" && -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "  → Created ${ENV_FILE} — edit it and set STRIPE_API_KEY (sk_test_…)."
fi

# Sanity-check docker.
if ! command -v docker >/dev/null 2>&1; then
    echo "  ⚠ docker not found in PATH — install Docker before using stripe-cli."
    exit 0
fi

cat <<EOF
  → Ready. Once STRIPE_API_KEY is set:
      grab exec stripe-cli listen      # start the webhook listener
      grab exec stripe-cli trigger     # fire payment_intent.succeeded
EOF
