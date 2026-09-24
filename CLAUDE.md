# INSPIRE MCP Search

Semantic search over INSPIRE-HEP abstracts: embeddings with Ollama
(nomic-embed-text, 768 dimensions) stored in PostgreSQL/pgvector, exposed
through an MCP server.

## Status

Early-stage scaffold. Only the container/infrastructure layer exists (three commits).

Licensed AGPL-3.0.

## Environment

- Infrastructure already working: compose.yml with `ollama` and `db` services,
  managed through `./manage_dev.sh` (wrapper around `docker compose`).
- Configuration lives in `.env` (template: `env_dist`): `DB_HOST=127.0.0.1`,
  `POSTGRES_*`, `OLLAMA_PORT`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_RAG_MODEL`.
- Python code runs on the host in a venv, not in a container.

## Environment setup

`.env` is gitignored and is required by both `compose.yml` (variable interpolation, and `env_file:` for the `db` service) and `manage_dev.sh`. Bootstrap it from the template:

```bash
cp env_dist .env   # then replace the `changeme` Postgres values
```

`MY_ENV` must be `dev` or `manage_dev.sh` refuses to run (guard against pointing the dev wrapper at a non-dev stack).

## Commands

All container operations go through `manage_dev.sh`, which wraps `docker compose -p $MY_PROJECT -f compose.yml` and additionally layers `compose.dev.yml` when that file exists. Any `docker compose` subcommand passes through:

```bash
./manage_dev.sh up -d
./manage_dev.sh logs -f ollama
./manage_dev.sh ps
./manage_dev.sh down
```

Pull the embedding/RAG models into the Ollama volume after first start:

```bash
./manage_dev.sh exec ollama ollama pull nomic-embed-text   # $OLLAMA_EMBEDDING_MODEL
./manage_dev.sh exec ollama ollama pull llama3.1:8b        # $OLLAMA_RAG_MODEL
```

## Architecture

Two services on a dedicated bridge network (`mynet`, subnet `$DOCKER_SUBNET`), both published only to `$BIND_HOST` (`127.0.0.1` by default) rather than all interfaces:

- **ollama** — serves both the embedding model and the RAG generation model. Requires an NVIDIA GPU (`deploy.resources.reservations.devices`); on a host without one, compose will fail to start the service. Container port 11434 → host `$OLLAMA_PORT` (11433, deliberately offset from the default). Models persist in the `ollama_data` volume.
- **db** — `pgvector/pgvector` on Postgres 18, holding the vector store. `db/init/*.sql` runs once, on an empty data volume only, via the image's `docker-entrypoint-initdb.d` hook; `01-extensions.sql` creates the `vector` extension. Changes to those files have no effect on an already-initialized `pg18` volume — the volume must be dropped and recreated.

The intended data flow is ingest → embed via Ollama → store vectors in pgvector → serve search over MCP; the ingest and MCP-server halves are not written yet.

## Current step: ingest.py

- Single download from https://inspirehep.net/api/literature with
  q="dark matter detection", size=500, sort=mostcited,
  fields=control_number,titles,abstracts,authors.full_name,
  publication_info.year,arxiv_eprints. Cache the raw response in
  data/inspire_raw.json; if the file exists, do not download again.
- normalize(): map each record to {id, title, abstract, url, metadata};
  skip records without an abstract.
- Table `papers` (id integer PK, title, abstract, url, metadata jsonb,
  embedding vector(768)), created with CREATE TABLE IF NOT EXISTS.
- Embeddings in batches via /api/embed, with the prefix "search_document: ".
- INSERT ... ON CONFLICT (id) DO UPDATE; register_vector from pgvector.psycopg.
- HNSW index with vector_cosine_ops, created at the end.
- Dependencies: httpx, psycopg[binary], pgvector, python-dotenv.
  No LangChain/LlamaIndex, no dedicated Ollama client.

## Rules

- Do not create or modify files unless I ask you to.
- Write one function at a time and explain each choice before moving on
  to the next one.

