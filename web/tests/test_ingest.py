from papers.management.commands.ingest_inspire import Command


def test_normalize_skips_records_without_abstract():
    hit = {"metadata": {"control_number": 42, "titles": [{"title": "T"}]}}

    assert Command()._normalize(hit) is None


def test_normalize_extracts_metadata():
    hit = {"metadata": {
        "control_number": 42,
        "titles": [{"title": "A title"}],
        "abstracts": [{"value": "An abstract"}],
        "authors": [{"full_name": "Doe, Jane"}],
        "publication_info": [{"year": 1999}],
        "arxiv_eprints": [{"value": "hep-ph/9901001"}],
    }}

    paper = Command()._normalize(hit)

    assert paper.id == 42
    assert paper.title == "A title"
    assert paper.url == "https://inspirehep.net/literature/42"
    assert paper.metadata["year"] == 1999
    assert paper.metadata["authors"] == ["Doe, Jane"]
