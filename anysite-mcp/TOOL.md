Crawl any website's docs into clean .md files (frontmatter keeps the source URL + title) ready for grepai / ripgrep indexing.

Despite the name, this is a standalone Python crawler — not an MCP server. It discovers
pages via `/llms.txt`, `/sitemap.xml`, or a same-domain BFS, prefers the markdown variant
of each page when one is served, and falls back to main-content extraction.

## Install

```bash
grab add anysite-mcp --hook
```

The `--hook` runs `post-grab.sh`, which creates a local virtualenv and installs
`trafilatura` + `markdownify`. Without `--hook`, the first `grab exec` builds it lazily.

## Usage

```bash
grab exec anysite-mcp https://docs.example.com
grab exec anysite-mcp https://docs.example.com --out ./docs_md --max-pages 300
grab exec anysite-mcp https://docs.example.com --delay 0.5 --no-full
```

Options:
- `--out <dir>`      output folder (default `./docs_md`)
- `--max-pages <n>`  page cap (default 500)
- `--delay <s>`      pause between requests (default 0.3)
- `--no-full`        skip the `/llms-full.txt` shortcut and crawl page by page

## Then index it (100% local, via Ollama)

```bash
ollama pull nomic-embed-text
cd docs_md && grepai watch --no-ui
grepai search "how to configure authentication"
```

## Notes

- A `.venv/` is created inside the installed tool dir on first run — it lives under
  `.grab/tools/` so it stays out of your project's git.
- Requires `python3` (>= 3.10 for the type hints used in `main.py`).
- A `.devcontainer/` ships alongside for editing the crawler itself; it is not used by `grab exec`.
