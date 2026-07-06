import subprocess
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django_tasks import task


@task()
def generate_thumbnail(media_item_id: int) -> None:
    from content.models import MediaItem

    media = MediaItem.objects.get(pk=media_item_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "thumb.jpg"

        if media.is_video:
            # Extract a frame at 1 second (or start of file if shorter)
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", "1",
                    "-i", media.file.url,
                    "-frames:v", "1",
                    "-vf", "scale=320:-1",
                    str(out_path),
                ],
                check=True,
                capture_output=True,
            )
        else:
            # For images, use ffmpeg to produce a scaled JPEG
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", media.file.url,
                    "-vf", "scale=320:-1",
                    str(out_path),
                ],
                check=True,
                capture_output=True,
            )

        thumb_name = f"{media_item_id}_thumb.jpg"
        media.thumbnail.save(thumb_name, ContentFile(out_path.read_bytes()), save=True)
