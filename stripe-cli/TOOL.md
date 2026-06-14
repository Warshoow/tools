Run the Stripe CLI (webhook listener + event triggers) via Docker, configured from a local .env.stripe.

A thin wrapper over the official `stripe/stripe-cli` image so you can listen for webhooks
and trigger test events without installing the CLI natively or remembering long
`docker run` incantations.

## Install

```bash
grab add stripe-cli --hook
```

The `--hook` runs `post-grab.sh`: it seeds `.env.stripe` from `.env.stripe.example`.
Then edit `.env.stripe` and set your test key:

```
STRIPE_API_KEY="sk_test_…"
PORT=3333                       # port your local app listens on
HOST=host.docker.internal       # where to forward webhooks (Docker → host)
```

## Usage

```bash
grab exec stripe-cli listen                                  # forward webhooks to your app
grab exec stripe-cli trigger                                 # payment_intent.succeeded (default)
grab exec stripe-cli trigger payment_intent.payment_failed
grab exec stripe-cli trigger customer.subscription.created
grab exec stripe-cli <subcommand> …                          # passthrough to the Stripe CLI
```

When `listen` starts it prints a `whsec_…` signing secret — copy it into your app's
`STRIPE_WEBHOOK_SECRET`.

## Common test events

`payment_intent.succeeded` · `payment_intent.payment_failed` · `payment_intent.created` ·
`customer.subscription.created` · `customer.subscription.updated` ·
`customer.subscription.deleted` · `customer.created`

## Troubleshooting

- **Webhook receives nothing** — make sure your app binds to `0.0.0.0` (not `127.0.0.1`)
  so the container can reach it via `host.docker.internal`, and that `PORT` matches.
- **Secret mismatch** — the `STRIPE_WEBHOOK_SECRET` in your app must equal the `whsec_…`
  printed by `listen`.

## Notes

- `.env.stripe` holds your secret API key — it is gitignored here and lives under
  `.grab/tools/`, so it never lands in your project's repo.
- The repo also ships `stripe-listen.sh`, `stripe-trigger.sh` and a
  `docker-compose.stripe.yml` for running things by hand; `run.sh` supersedes them for
  the `grab exec` flow.
