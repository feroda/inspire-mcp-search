# INSPIRE MCP Search

Semantic search over INSPIRE-HEP abstracts: embeddings with Ollama
(nomic-embed-text, 768 dimensions) stored in PostgreSQL/pgvector, exposed
through an MCP server.

## Status

Working vertical slice: ingest -> embed -> store -> search, exposed over both a
DRF endpoint and an MCP server, with tests and CI. See README.md for the
architecture and the design decisions behind it.

Licensed AGPL-3.0.

## Layout

Django lives in `web/`, bind-mounted to `/app` in the container.

- `web/inspire/` — project package (settings, urls, wsgi)
- `web/papers/` — the single app: `models.Paper`, `embeddings`, `search`,
  `views`, and two management commands (`ingest_inspire`, `mcp_server`)
- `web/tests/` — pytest-django; embeddings stubbed with orthogonal unit vectors
- `db/init/` — runs once, on an empty volume, for the main database only

## Commands

Everything goes through `./manage_dev.sh`, which wraps
`docker compose -p $MY_PROJECT -f compose.yml`, layers `compose.dev.yml` if it
exists and `compose.gpu.yml` when `USE_GPU=1`, and turns `django <cmd>` into
`exec web python ./manage.py <cmd>` via `compose_final_exec.sh`.

```bash
./manage_dev.sh up -d
./manage_dev.sh django migrate
./manage_dev.sh django ingest_inspire --max-records 2000
./manage_dev.sh run --rm web pytest -q
./manage_dev.sh run --rm web ruff check .
./manage_dev.sh exec ollama ollama pull nomic-embed-text
```

## Conventions

- Config through `django-environ`: declare the variable with its type and
  default in the `environ.Env(...)` call in `settings.py`, then read it with
  `env("NAME")`. Add every new variable to `env_dist` as well.
- Inside the compose network, use service names and internal ports
  (`DB_HOST=db`, `OLLAMA_URL=http://ollama:11434`). The host mappings
  (`$WEB_PORT`, `$OLLAMA_PORT`, `$POSTGRES_PORT`) are for debugging only.
- The container runs as `$DOCKER_UID:$DOCKER_GID` so files written into the
  bind mount (migrations, the raw cache) belong to the developer, not root.
- Retrieval logic belongs in `papers/search.py`. The REST view and the MCP
  tools are thin callers; do not duplicate a query in either.
- Embedding prefixes live in settings and are applied inside
  `papers/embeddings.py` — callers pass raw text.
- MCP tools run in an event loop, so any ORM access must go through
  `sync_to_async(..., thread_sensitive=True)`.
- `mcp` is v2.x: the server class is `MCPServer`, not `FastMCP`.

## Rules

- You may create and modify source files directly, without asking first.
- Work tool by tool, not function by function: batch independent edits,
  and explain only what is non-obvious or what I would be asked about in
  an interview.
- Keep `tmp.md` (gitignored) as the running study file: append anything I
  would need to defend in an interview but have not yet internalised.

