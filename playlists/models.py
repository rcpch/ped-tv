from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


class Playlist(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PRESSING = "pressing", "Pressing…"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    is_main = models.BooleanField(
        default=False,
        help_text="Display this playlist on the front page",
    )

    # Pressed artefacts
    mp4_file = models.FileField(upload_to="playlists/mp4/", blank=True)
    hls_manifest = models.FileField(upload_to="playlists/hls/", blank=True)
    poster = models.ImageField(upload_to="playlists/posters/", blank=True)
    press_task_id = models.CharField(max_length=64, blank=True)
    press_error = models.TextField(blank=True)
    pressed_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="playlists",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        # Enforce single main playlist
        if self.is_main:
            Playlist.objects.exclude(pk=self.pk).filter(is_main=True).update(
                is_main=False
            )
        super().save(*args, **kwargs)

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def is_visible(self):
        return self.status == self.Status.PUBLISHED


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="items"
    )
    media_item = models.ForeignKey(
        "content.MediaItem", on_delete=models.PROTECT, related_name="playlist_items"
    )
    order = models.PositiveIntegerField(default=0)
    # Display duration in seconds for image items (not used for videos)
    duration = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = [("playlist", "media_item")]

    def __str__(self):
        return f"{self.playlist} — {self.media_item} (#{self.order})"

    @property
    def effective_duration(self):
        """Display duration in seconds; defaults to 10s if not explicitly set."""
        return self.duration if self.duration is not None else 10
