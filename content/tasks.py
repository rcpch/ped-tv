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

        # ---- Infer media type ----
        # Videos have a measurable duration; still images report "N/A".
        probe = subprocess.run(
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
            duration_val = float(probe.stdout.strip())
            is_video = duration_val > 0.5  # single-frame "videos" are treated as images
        except ValueError:
            is_video = False  # "N/A" or empty → image

        media.media_type = MediaItem.MediaType.VIDEO if is_video else MediaItem.MediaType.IMAGE

        # ---- Generate thumbnail ----
        if is_video:
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
            media.video_duration = duration_val
        else:
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

        # Save thumbnail and all inferred fields in one write
        thumb_name = f"{media_item_id}_thumb.jpg"
        media.thumbnail.save(thumb_name, ContentFile(out_path.read_bytes()), save=False)
        media.save(update_fields=["media_type", "video_duration", "thumbnail"])
