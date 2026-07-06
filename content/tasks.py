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
        tmp = Path(tmpdir)
        out_path = tmp / "thumb.jpg"

        # Download the source file via storage backend (internal endpoint, not public URL)
        suffix = Path(media.file.name).suffix or ".bin"
        src_path = tmp / f"source{suffix}"
        with media.file.open("rb") as f:
            src_path.write_bytes(f.read())

        if media.is_video:
            # Extract a frame at 1 second (or start of file if shorter)
            subprocess.run(
                [
                    "ffmpeg", "-nostdin", "-y",
                    "-ss", "1",
                    "-i", str(src_path),
                    "-frames:v", "1",
                    "-vf", "scale=320:-1",
                    str(out_path),
                ],
                check=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )
            # Probe clip duration while we have the file locally.
            # Note: ffprobe does not support -nostdin; use stdin=DEVNULL instead.
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(src_path),
                ],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
            )
            try:
                media.video_duration = float(result.stdout.strip())
            except (ValueError, TypeError):
                pass
        else:
            # For images, use ffmpeg to produce a scaled JPEG
            subprocess.run(
                [
                    "ffmpeg", "-nostdin", "-y",
                    "-i", str(src_path),
                    "-vf", "scale=320:-1",
                    str(out_path),
                ],
                check=True,
                capture_output=True,
                stdin=subprocess.DEVNULL,
            )

        thumb_name = f"{media_item_id}_thumb.jpg"
        media.thumbnail.save(thumb_name, ContentFile(out_path.read_bytes()), save=True)
        if media.video_duration is not None:
            media.save(update_fields=["video_duration"])
