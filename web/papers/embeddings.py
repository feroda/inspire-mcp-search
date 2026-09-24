"""Thin client for the Ollama embedding endpoint.

Deliberately not using an SDK or a framework: one HTTP call, explicit batching,
no hidden retries. Four dependencies are easier to maintain for years than one
abstraction layer.
"""

import httpx
from django.conf import settings


def embed(texts, prefix, batch_size=32, timeout=120.0):
    """Embed `texts`, prefixed for their role, returning one vector each.

    `prefix` matters: nomic-embed-text is trained asymmetrically, so documents
    and queries are embedded differently and mixing them up silently degrades
    relevance rather than raising.
    """
    vectors = []
    url = f"{settings.OLLAMA_URL}/api/embed"

    with httpx.Client(timeout=timeout) as client:
        for start in range(0, len(texts), batch_size):
            batch = [prefix + t for t in texts[start:start + batch_size]]
            response = client.post(
                url,
                json={"model": settings.OLLAMA_EMBEDDING_MODEL, "input": batch},
            )
            response.raise_for_status()
            vectors.extend(response.json()["embeddings"])

    return vectors


def embed_documents(texts, **kwargs):
    return embed(texts, settings.EMBEDDING_DOCUMENT_PREFIX, **kwargs)


def embed_query(text, **kwargs):
    return embed([text], settings.EMBEDDING_QUERY_PREFIX, **kwargs)[0]
