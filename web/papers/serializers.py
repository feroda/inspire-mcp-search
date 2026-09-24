from rest_framework import serializers

from .models import Paper


class PaperSerializer(serializers.ModelSerializer):
    # Annotated by the search queryset; absent when a Paper is serialized
    # outside a search context.
    score = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = ("id", "title", "abstract", "url", "metadata", "score")

    def get_score(self, obj):
        distance = getattr(obj, "distance", None)
        if distance is None:
            return None
        # Cosine distance in [0, 2]; report similarity, which reads better.
        return round(1 - distance, 4)
