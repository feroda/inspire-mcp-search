"""Expose the search over the Model Context Protocol, on stdio.

The MCP server is deliberately a thin caller of papers.search: the retrieval
logic has exactly one implementation, shared with the REST API.
"""

from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from mcp.server.mcpserver import MCPServer

from papers.models import Paper
from papers.search import semantic_search

mcp = MCPServer("inspire-search")


@mcp.tool()
async def search_papers(query: str, limit: int = 5) -> list[dict]:
    """Search INSPIRE-HEP papers by meaning rather than keywords.

    Args:
        query: A natural-language description of the topic of interest.
        limit: How many papers to return (1-50).
    """
    limit = max(1, min(limit, 50))

    # The ORM is synchronous, and MCP tools run inside a live event loop:
    # calling it directly would raise SynchronousOnlyOperation.
    papers = await sync_to_async(list, thread_sensitive=True)(
        semantic_search(query, limit=limit)
    )

    return [
        {
            "id": p.id,
            "title": p.title,
            "abstract": p.abstract,
            "url": p.url,
            "year": p.metadata.get("year"),
            "authors": p.metadata.get("authors", []),
            "similarity": round(1 - p.distance, 4),
        }
        for p in papers
    ]


@mcp.tool()
async def get_paper(paper_id: int) -> dict:
    """Fetch one INSPIRE-HEP paper by its control number."""
    paper = await sync_to_async(
        Paper.objects.filter(id=paper_id).first, thread_sensitive=True
    )()
    if paper is None:
        return {"error": f"No paper with id {paper_id}"}

    return {
        "id": paper.id,
        "title": paper.title,
        "abstract": paper.abstract,
        "url": paper.url,
        "metadata": paper.metadata,
    }


class Command(BaseCommand):
    help = "Run the MCP server (stdio transport)."

    def handle(self, *args, **options):
        mcp.run(transport="stdio")
