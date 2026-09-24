from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .search import semantic_search
from .serializers import PaperSerializer

MAX_LIMIT = 50


class SearchView(APIView):
    """GET /api/search/?q=...&limit=10 — semantic search over abstracts."""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"detail": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = min(int(request.query_params.get("limit", 10)), MAX_LIMIT)
        except ValueError:
            return Response(
                {"detail": "Query parameter 'limit' must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = semantic_search(query, limit=limit)
        return Response({
            "query": query,
            "count": len(results),
            "results": PaperSerializer(results, many=True).data,
        })
