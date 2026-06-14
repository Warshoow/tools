#!/usr/bin/env bash
set -euo pipefail

# Entrypoint for `grab exec stripe-cli <cmd> [args]`.
# Wraps the official stripe/stripe-cli Docker image, reading config from the
# .env.stripe sitting next to this script.
#
# Usage:
#   grab exec stripe-cli listen                          # forward webhooks to your local app
#   grab exec stripe-cli trigger                         # trigger payment_intent.succeeded
#   grab exec stripe-cli trigger customer.subscription.created
#   grab exec stripe-cli <anything>                      # passthrough to the stripe CLI

HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${HERE}/.env.stripe"
IMAGE="stripe/stripe-cli:latest"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "✖ ${ENV_FILE} not found. Run: grab hook stripe-cli" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${STRIPE_API_KEY:-}" || "$STRIPE_API_KEY" == "sk_test_...."* ]]; then
    echo "✖ STRIPE_API_KEY is not set in ${ENV_FILE}." >&2
    exit 1
fi

HOST="${HOST:-host.docker.internal}"
PORT="${PORT:-3333}"

cmd="${1:-listen}"
[[ $# -gt 0 ]] && shift

case "$cmd" in
    listen)
        FORWARD="http://${HOST}:${PORT}/webhooks/stripe"
        echo "→ Forwarding Stripe webhooks to ${FORWARD}" >&2
        echo "  (copy the printed whsec_… into your app's STRIPE_WEBHOOK_SECRET)" >&2
        exec docker run --rm -it "$IMAGE" \
            listen --api-key "$STRIPE_API_KEY" \
            --forward-to "$FORWARD" \
            ${APP_DOMAIN:+--headers "Host:${APP_DOMAIN}"} \
            "$@"
        ;;
    trigger)
        event="${1:-payment_intent.succeeded}"
        [[ $# -gt 0 ]] && shift
        echo "→ Triggering ${event}" >&2
        exec docker run --rm -it "$IMAGE" \
            trigger "$event" --api-key "$STRIPE_API_KEY" "$@"
        ;;
    *)
        # Passthrough for any other stripe subcommand (logs, fixtures, ...).
        exec docker run --rm -it "$IMAGE" "$cmd" --api-key "$STRIPE_API_KEY" "$@"
        ;;
esac
