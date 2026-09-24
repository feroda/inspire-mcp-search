import pytest

from papers import search as search_module
from tests.conftest import unit_vector


@pytest.fixture
def stub_embedding(monkeypatch):
    monkeypatch.setattr(search_module, "embed_query", lambda text: unit_vector(0))


def test_search_returns_scored_results(client, papers, stub_embedding):
    response = client.get("/api/search/", {"q": "dark matter", "limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "dark matter"
    assert body["results"][0]["id"] == 1
    # Identical vectors: cosine distance 0, so similarity 1.
    assert body["results"][0]["score"] == pytest.approx(1.0, abs=1e-3)


def test_missing_query_is_a_client_error(client, db):
    assert client.get("/api/search/").status_code == 400


def test_non_integer_limit_is_a_client_error(client, db):
    assert client.get("/api/search/", {"q": "x", "limit": "many"}).status_code == 400
