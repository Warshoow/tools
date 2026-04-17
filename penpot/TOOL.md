Self-hosted Penpot (open-source Figma alternative) via docker compose.

Wraps the upstream docker-compose with a tiny CLI: up, down, logs, status, pull.
Data persists in named docker volumes so it survives `grab remove`.

Pinned via PENPOT_VERSION in .env — bump intentionally, then `grab exec penpot pull && grab exec penpot up`.

## Install

```bash
grab add penpot --hook
```

The `--hook` runs `post-grab.sh` automatically: it seeds `.env` from `.env.example`
and generates a fresh `PENPOT_SECRET_KEY`. Without `--hook`, grab will ask.

## Usage

```bash
grab exec penpot up        # start (detached)
grab exec penpot logs      # follow logs
grab exec penpot status    # docker compose ps
grab exec penpot pull      # pull pinned image versions
grab exec penpot down      # stop
grab exec penpot <any>     # passthrough to `docker compose`
```

URLs once running:
- Penpot UI: http://localhost:9001
- Mailcatch (dev SMTP inbox): http://localhost:1080

## Bumping the Penpot version

1. Edit `PENPOT_VERSION=` in `.env` (or `.env.example` upstream and re-seed).
2. `grab exec penpot pull`
3. `grab exec penpot up`

## Notes

- `.env` is created on first install with a per-machine secret key. Never commit it.
- Volumes (`penpot_postgres_v15`, `penpot_assets`) are managed by docker. Use
  `docker volume rm` if you ever need a clean wipe — `grab remove penpot` won't
  touch them.
