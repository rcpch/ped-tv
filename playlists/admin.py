from django.contrib import admin
from .models import Playlist, PlaylistItem


class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 0
    ordering = ["order"]


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "is_main", "created_by", "created_at"]
    list_filter = ["status", "is_main"]
    search_fields = ["title"]
    readonly_fields = ["slug", "press_task_id", "pressed_at", "created_at", "updated_at"]
    inlines = [PlaylistItemInline]
