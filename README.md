# INSPIRE MCP Search

Semantic search over [INSPIRE-HEP](https://inspirehep.net) literature
abstracts. Abstracts are embedded with a local Ollama model, stored as vectors
in PostgreSQL/pgvector, and served two ways: as a REST API for applications,
and over the [Model Context Protocol](https://modelcontextprotocol.io) so an
LLM agent can search the literature as a tool.

Searching for *"an experiment that must be free of radioactive
contamination"* returns *"Removing krypton from xenon by cryogenic
distillation to the ppq level"* first. The query and the title share no word
at all: the match requires knowing that krypton removal from xenon is how
rare-event experiments achieve radiopurity. A keyword index returns nothing
useful here.

## Architecture

```
INSPIRE-HEP API
      │  ingest_inspire (Django management command)
      │  fetch → cache → normalize → upsert → embed in batches
      ▼
┌─────────────┐   embeddings    ┌──────────┐
│  Postgres   │◄────────────────│  Ollama  │  nomic-embed-text, 768 dims
│  + pgvector │                 └──────────┘
│  HNSW index │                       ▲
└─────────────┘                       │ query embedding
      ▲                               │
      │  papers.search.semantic_search()
      │
      ├── REST:  GET /api/search/?q=…   (Django + DRF)
      └── MCP :  search_papers / get_paper tools (stdio)
```

Both entry points call the same `semantic_search()`, so retrieval has exactly
one implementation.

## Quickstart

Requires Docker with Compose. A GPU is optional — Ollama runs on CPU by
default.

```bash
cp env_dist .env          # then set POSTGRES_* and SECRET_KEY
./manage_dev.sh up -d
./manage_dev.sh exec ollama ollama pull nomic-embed-text
./manage_dev.sh django migrate
./manage_dev.sh django ingest_inspire --query "dark matter detection" --max-records 2000
```

Ingest takes a few minutes: it pages through the INSPIRE API, caches the raw
response under `web/data/`, and embeds in batches. Re-running is safe — the
raw response is reused and records upsert on INSPIRE's control number.

With an NVIDIA GPU, set `USE_GPU=1` in `.env` to layer `compose.gpu.yml`.

### Search over REST

```bash
curl "http://127.0.0.1:9001/api/search/?q=an+experiment+that+must+be+free+of+radioactive+contamination&limit=3"
```

```json
{
  "query": "an experiment that must be free of radioactive contamination",
  "count": 3,
  "results": [
    {
      "id": 1503216,
      "title": "Removing krypton from xenon by cryogenic distillation to the ppq level",
      "abstract": "…",
      "url": "https://inspirehep.net/literature/1503216",
      "metadata": {"year": 2017, "arxiv": ["1612.04284"], "authors": ["Aprile, E.", "Aalbers, J."]},
      "score": 0.6905
    },
    {
      "id": 1598175,
      "title": "Material radioassay and selection for the XENON1T dark matter experiment",
      "abstract": "…",
      "url": "https://inspirehep.net/literature/1598175",
      "metadata": {"year": 2017, "arxiv": ["1705.01828"], "authors": ["Aprile, E.", "Aalbers, J."]},
      "score": 0.689
    },
    {
      "id": 1356249,
      "title": "Lowering the radioactivity of the photomultiplier tubes for the XENON1T dark matter experiment",
      "abstract": "…",
      "url": "https://inspirehep.net/literature/1356249",
      "metadata": {"year": 2015, "arxiv": ["1503.07698"], "authors": ["Aprile, E.", "Agostini, F."]},
      "score": 0.6825
    }
  ]
}
```

All three results are radiopurity papers — the concept the query describes
without naming it. The top hit shares no word with the query at all.

### Search over MCP

```bash
./manage_dev.sh run --rm web python manage.py mcp_server
```

Speaks MCP over stdio and exposes two tools, `search_papers(query, limit)` and
`get_paper(paper_id)`, so an agent can cite specific INSPIRE records instead
of recalling them from training data.

## Design notes

**Query and document embeddings are not symmetric.** `nomic-embed-text` is
trained with distinct prefixes: documents are embedded as
`search_document: …` and queries as `search_query: …`. Getting this wrong
degrades relevance silently rather than raising, so the prefixes live in
settings and are applied by `papers.embeddings`, never by callers.

**The index operator class must match the query operator.** The HNSW index is
built with `vector_cosine_ops`, and the query uses `CosineDistance` (`<=>`).
A mismatch still returns correct rows — via a sequential scan — so it is
invisible until the table is large.

**The planner had to be told what a distance costs.** Out of the box,
Postgres preferred a sequential scan (12.2ms measured) over the HNSW index
(1.4ms when forced with `enable_seqscan = off`). The planner compares
estimated costs, not times, and both estimates were wrong: pgvector declares
`cosine_distance` with the default `procost` of 1 — the cost of comparing two
integers — so a 768-dimensional distance, roughly 768 multiply-adds, was
costed as free, while the HNSW scan carried a conservative startup estimate of
891.32 against the sequential scan's total of 739.98. Migration
`0002_distance_function_cost` declares a truthful cost, after which the
planner chooses the index unaided. `EXPLAIN ANALYZE` is the only way to catch
this: the wrong plan returns correct rows, just slowly.

**The `vector` extension is created in a migration, not only in
`db/init/`.** The init script runs once, for the main database, on an empty
volume — but Django creates the test database itself, so without
`VectorExtension()` as the first migration operation every test fails on an
unknown type.

**Ingest is three separable phases.** Fetch, upsert and embed are independent,
so a failure in one does not force redoing the others, and `--skip-embeddings`
allows loading metadata before a model is available.

**No LangChain or LlamaIndex.** Four dependencies, explicit SQL through the
ORM, and one HTTP call to Ollama. For code meant to be maintained for years,
transparency beats abstraction.

## Tests

```bash
./manage_dev.sh run --rm web pytest -q
./manage_dev.sh run --rm web ruff check .
```

Embeddings are stubbed with orthogonal unit vectors, so retrieval behaviour is
asserted exactly and the suite runs without a model server — which is what
lets CI run it on every push.

## Next steps

- **Hybrid search.** Vector search is weak on exact tokens (arXiv identifiers,
  collaboration names, author surnames) where lexical search is strong. The
  next step is Postgres full-text search fused with the vector ranking by
  reciprocal rank fusion — closer to how INSPIRE's own OpenSearch works.
- **RAG.** `OLLAMA_RAG_MODEL` is configured but unused. Retrieval is the hard
  half and it is done; a generation layer answering questions with citations
  back to INSPIRE records is a thin addition on top.
- **Scheduled ingest.** The ingest phases map onto an Airflow DAG with
  per-phase retries, replacing the manual command for continuous updates.

## Notes

Built with AI assistance (Claude Code); the architecture, technical decisions
and review are my own.

Licensed under AGPL-3.0.
