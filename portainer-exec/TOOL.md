Run shell scripts in a Docker container through the Portainer API — sync for short ones, detached + wait for long ones (results survive dropped connections).

## Config

Read from env, else from `env` in `<project>/.claude/settings.local.json`:

- `PORTAINER_URL` (e.g. `https://10.0.0.1:9443`, self-signed certs accepted)
- `PORTAINER_ENDPOINT` (Portainer environment id)
- `PORTAINER_ACCESS_TOKEN` (never printed)

## Usage

```bash
grab exec portainer-exec ps [filter]                     # containers + state
grab exec portainer-exec run   <container> <script.sh>   # sync, ≤ 10 min
grab exec portainer-exec start <container> <script.sh> <name>   # detached
grab exec portainer-exec poll  <container> <name>        # output so far + RUNNING / DONE rc=N
grab exec portainer-exec wait  <container> <name> [max_min=30]  # poll every 30 s until DONE
```

`start` writes the script to `/tmp/pe_<name>.sh` in the container and runs it with `nohup`;
output goes to `/tmp/pe_<name>.out`, exit code to `/tmp/pe_<name>.rc`. Use `wait` for
anything that can last more than a few minutes: the HTTP exec of `run` is cut at 10 min and
the output is lost. Scripts are sent base64-encoded, so quotes need no escaping.
