from django.contrib import admin

from .models import Paper


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "has_embedding")
    search_fields = ("title", "abstract")

    @admin.display(boolean=True, description="embedded")
    def has_embedding(self, obj):
        return obj.embedding is not None
