Drop a ready-to-use VSCode devcontainer (Docker Compose + Postgres + Claude Code) into the project root.

A reusable dev environment for Node/Adonis/Vue projects: an `app` service built from
`Dockerfile.dev` plus a `postgres:16` service, with Claude Code installed, your
`~/.gitconfig` / `~/.ssh` / `grab` bind-mounted in, and a curated VSCode extension set.

## Install

```bash
grab add devcontainer --hook
```

The `--hook` runs `post-grab.sh`, which copies the files into place (asking before
overwriting an existing `.devcontainer/`):

```
<project>/.devcontainer/devcontainer.json
<project>/.devcontainer/setup-dev.sh
<project>/Dockerfile.dev
<project>/docker-compose.dev.yml
```

Without `--hook`, grab asks; run it later with `grab hook devcontainer`.

## Then

Open the project in VSCode and **Reopen in Container**. On creation it runs
`setup-dev.sh`, which installs Claude Code, marks `/app` a safe git directory, and adds a
git-aware prompt.

## What you get

- `app` service on port **3333**, source bind-mounted at `/app`, named-volume
  `node_modules`
- `db` service: `postgres:16-alpine` on **5432** (set its `POSTGRES_*` env before first run)
- Mounts: `~/.claude-pro` → `/root/.claude`, `~/.gitconfig`, `~/.ssh` (ro), the host's
  `grab` binary, and the Docker socket

## Notes

- After copying, review `docker-compose.dev.yml` and fill in the empty `POSTGRES_USER/
  PASSWORD/DB` and the `${TZ}`, `${APP_KEY}`, etc. environment values (typically from your
  project's `.env`).
- `devcontainer.json` targets the compose `app` service and `../docker-compose.dev.yml` —
  keep those in sync if you rename either.
