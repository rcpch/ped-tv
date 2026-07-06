from django.contrib import admin
from .models import MediaItem


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ["title", "media_type", "provider", "uploaded_by", "created_at"]
    list_filter = ["media_type", "provider"]
    search_fields = ["title"]
    readonly_fields = ["created_at"]
