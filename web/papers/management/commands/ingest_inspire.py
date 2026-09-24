"""Fetch INSPIRE-HEP records, store them, and embed their abstracts.

Three separable phases — fetch, upsert, embed — so a failure in one does not
force redoing the others. The raw API response is cached on disk: re-running
ingest must not hammer INSPIRE.
"""

import json
import time

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand

from papers.embeddings import embed_documents
from papers.models import Paper

FIELDS = ",".join([
    "control_number",
    "titles",
    "abstracts",
    "authors.full_name",
    "publication_info.year",
    "arxiv_eprints",
])

# INSPIRE caps page size at 1000; 250 keeps single responses small.
PAGE_SIZE = 250


class Command(BaseCommand):
    help = "Ingest INSPIRE-HEP literature records and embed their abstracts."

    def add_arguments(self, parser):
        parser.add_argument("--query", default="dark matter detection",
                            help="INSPIRE search query (the `q` parameter).")
        parser.add_argument("--max-records", type=int, default=2000,
                            help="Stop after roughly this many records.")
        parser.add_argument("--refresh", action="store_true",
                            help="Re-download even if the raw cache exists.")
        parser.add_argument("--skip-embeddings", action="store_true",
                            help="Store records only; embed in a later run.")

    def handle(self, *args, **options):
        records = self._fetch(options["query"], options["max_records"],
                              refresh=options["refresh"])
        papers = [p for p in map(self._normalize, records) if p]
        self.stdout.write(f"{len(papers)} records with an abstract")

        created = self._upsert(papers)
        self.stdout.write(self.style.SUCCESS(f"stored {created} records"))

        if not options["skip_embeddings"]:
            self._embed_missing()

    # -- fetch ------------------------------------------------------------

    def _fetch(self, query, max_records, refresh=False):
        cache = settings.INSPIRE_RAW_CACHE

        if cache.exists() and not refresh:
            self.stdout.write(f"using cached {cache}")
            return json.loads(cache.read_text())

        hits = []
        page = 1
        with httpx.Client(timeout=60.0) as client:
            while len(hits) < max_records:
                self.stdout.write(f"fetching page {page} ({len(hits)} so far)")
                response = client.get(settings.INSPIRE_API_URL, params={
                    "q": query,
                    "size": PAGE_SIZE,
                    "page": page,
                    "sort": "mostcited",
                    "fields": FIELDS,
                })
                response.raise_for_status()
                batch = response.json()["hits"]["hits"]
                if not batch:
                    break
                hits.extend(batch)
                page += 1
                # INSPIRE asks for courtesy; this is a bulk read of a public API.
                time.sleep(1)

        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(hits))
        self.stdout.write(f"cached {len(hits)} raw records to {cache}")
        return hits

    # -- normalize --------------------------------------------------------

    def _normalize(self, hit):
        """Map one API record to a Paper, or None when unusable."""
        meta = hit.get("metadata", {})

        abstracts = meta.get("abstracts") or []
        if not abstracts:
            # No abstract means nothing to embed: the record cannot take part
            # in semantic search, so it is dropped rather than stored empty.
            return None

        titles = meta.get("titles") or [{}]
        control_number = meta["control_number"]

        return Paper(
            id=control_number,
            title=titles[0].get("title", ""),
            abstract=abstracts[0].get("value", ""),
            url=f"https://inspirehep.net/literature/{control_number}",
            metadata={
                "authors": [a.get("full_name") for a in (meta.get("authors") or [])[:10]],
                "year": (meta.get("publication_info") or [{}])[0].get("year"),
                "arxiv": [e.get("value") for e in (meta.get("arxiv_eprints") or [])],
            },
        )

    def _upsert(self, papers):
        """Idempotent by INSPIRE control_number, so re-ingest is safe."""
        Paper.objects.bulk_create(
            papers,
            update_conflicts=True,
            update_fields=["title", "abstract", "url", "metadata"],
            unique_fields=["id"],
            batch_size=500,
        )
        return len(papers)

    # -- embed ------------------------------------------------------------

    def _embed_missing(self):
        pending = list(Paper.objects.filter(embedding=None))
        if not pending:
            self.stdout.write("nothing left to embed")
            return

        self.stdout.write(f"embedding {len(pending)} abstracts")
        # Title plus abstract: the title carries topic words the abstract
        # sometimes assumes.
        texts = [f"{p.title}\n\n{p.abstract}" for p in pending]

        vectors = embed_documents(texts)
        for paper, vector in zip(pending, vectors, strict=True):
            paper.embedding = vector

        Paper.objects.bulk_update(pending, ["embedding"], batch_size=200)
        self.stdout.write(self.style.SUCCESS(f"embedded {len(pending)} abstracts"))
