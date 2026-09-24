"""Semantic search over paper abstracts.

Kept free of HTTP concerns so that both the REST API and the MCP server are
thin callers of the same function.
"""

from pgvector.django import CosineDistance

from .embeddings import embed_query
from .models import Paper


def semantic_search(query, limit=10):
    """Return the `limit` papers closest to `query`, nearest first.

    CosineDistance maps to the `<=>` operator, which is what the HNSW index
    was built for (vector_cosine_ops). Using a different distance here would
    still return correct rows, but via a sequential scan.
    """
    query_vector = embed_query(query)

    return (
        Paper.objects.exclude(embedding=None)
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:limit]
    )
