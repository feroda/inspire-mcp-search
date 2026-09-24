import pytest
from django.conf import settings

from papers.models import Paper


def unit_vector(axis):
    """A 768-dim one-hot vector: exact, predictable cosine distances."""
    vector = [0.0] * settings.EMBEDDING_DIMENSIONS
    vector[axis] = 1.0
    return vector


@pytest.fixture
def papers(db):
    """Three papers whose embeddings are mutually orthogonal."""
    return [
        Paper.objects.create(
            id=1, title="Axions", abstract="On axion dark matter.",
            url="https://inspirehep.net/literature/1",
            metadata={"year": 2020}, embedding=unit_vector(0),
        ),
        Paper.objects.create(
            id=2, title="Neutrinos", abstract="On neutrino oscillation.",
            url="https://inspirehep.net/literature/2",
            metadata={"year": 2021}, embedding=unit_vector(1),
        ),
        Paper.objects.create(
            id=3, title="Unembedded", abstract="Not yet embedded.",
            url="https://inspirehep.net/literature/3",
            metadata={}, embedding=None,
        ),
    ]
