#!/bin/bash

# Script pour lancer stripe-cli facilement
# Usage: ./stripe-listen.sh
# Exemple: ./stripe-listen.sh

source ./.env.stripe

echo "Stripe listener started, forwarding to http://$HOST:$PORT/webhooks/stripe"
echo ""

docker run --rm -it \
  stripe/stripe-cli:latest \
  listen --api-key $STRIPE_API_KEY \
  --forward-to http://$HOST:$PORT/webhooks/stripe \
  --headers Host:${APP_DOMAIN}

echo ""
echo "Stripe listener stopped, forwarding to http://$HOST:$PORT/webhooks/stripe"