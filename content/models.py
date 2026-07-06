from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MediaItem(models.Model):
    class MediaType(models.TextChoices):
        VIDEO = "video", "Video"
        IMAGE = "image", "Image"

    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    file = models.FileField(upload_to="media/files/")
    thumbnail = models.ImageField(upload_to="media/thumbnails/", blank=True)
    provider = models.ForeignKey(
        "providers.Provider",
        on_delete=models.PROTECT,
        related_name="media_items",
    )
    # Duration in seconds; used for images (videos use actual clip length)
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Display duration in seconds (images only)",
    )
    # Probed from the file during thumbnail generation
    video_duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Clip length in seconds (videos only, populated automatically)",
    )
    title = models.CharField(max_length=200)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_media",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_video(self):
        return self.media_type == self.MediaType.VIDEO

    @property
    def is_image(self):
        return self.media_type == self.MediaType.IMAGE

    @property
    def duration_seconds(self):
        """Duration in seconds: video clip length or image display time."""
        if self.is_video:
            return self.video_duration
        return float(self.duration) if self.duration is not None else None
