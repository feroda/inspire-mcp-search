"""Retrieval tests.

Embeddings are stubbed rather than computed: these assert the *retrieval*
behaviour, which must be testable without a running model server.
"""

import pytest

from papers import search as search_module
from tests.conftest import unit_vector


@pytest.fixture
def query_matching_axions(monkeypatch):
    monkeypatch.setattr(search_module, "embed_query", lambda text: unit_vector(0))


def test_orders_by_cosine_distance(papers, query_matching_axions):
    results = list(search_module.semantic_search("anything", limit=10))

    assert [p.id for p in results] == [1, 2]
    assert results[0].distance < results[1].distance


def test_excludes_unembedded_papers(papers, query_matching_axions):
    results = search_module.semantic_search("anything", limit=10)

    # Paper 3 has no embedding: including it would make it sort arbitrarily.
    assert 3 not in [p.id for p in results]


def test_respects_limit(papers, query_matching_axions):
    assert len(search_module.semantic_search("anything", limit=1)) == 1
