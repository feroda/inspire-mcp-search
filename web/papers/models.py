from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class Paper(models.Model):
    """A single INSPIRE-HEP literature record with its abstract embedding."""

    # INSPIRE's own control_number, so re-ingesting is idempotent.
    id = models.IntegerField(primary_key=True)
    title = models.TextField()
    abstract = models.TextField()
    url = models.URLField()
    metadata = models.JSONField(default=dict)

    # Null until the record has been embedded, so ingest can insert rows and
    # embed them in a separate batched pass.
    embedding = VectorField(dimensions=settings.EMBEDDING_DIMENSIONS, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(
                name="paper_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                # Must match the operator used at query time (<=>), otherwise
                # Postgres silently falls back to a sequential scan.
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"[{self.id}] {self.title[:80]}"
