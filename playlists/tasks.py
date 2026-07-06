import subprocess
import tempfile
import traceback
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils import timezone
from django_tasks import task

# Target resolution for all pressed output
PRESS_WIDTH = 1280
PRESS_HEIGHT = 720
PRESS_FPS = 25


@task()
def press_playlist(playlist_id: int) -> None:
    from playlists.models import Playlist

    playlist = Playlist.objects.get(pk=playlist_id)
    try:
        _do_press(playlist)
    except Exception as exc:
        playlist.status = Playlist.Status.DRAFT
        playlist.press_error = traceback.format_exc()
        playlist.save(update_fields=["status", "press_error"])
        raise


def _do_press(playlist) -> None:
    from playlists.models import Playlist

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        clips = []

        for index, item in enumerate(playlist.items.select_related("media_item")):
            media = item.media_item
            suffix = Path(media.file.name).suffix or ".bin"
            local_path = tmp / f"input_{index}{suffix}"

            # Read file via storage backend (uses internal endpoint_url, not the public URL)
            with media.file.open("rb") as f:
                local_path.write_bytes(f.read())

            clip_path = tmp / f"clip_{index}.mp4"

            if media.is_video:
                # Normalise video to target resolution/fps
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", str(local_path),
                        "-vf", f"scale={PRESS_WIDTH}:{PRESS_HEIGHT}:force_original_aspect_ratio=decrease,"
                               f"pad={PRESS_WIDTH}:{PRESS_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                        "-r", str(PRESS_FPS),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        str(clip_path),
                    ],
                    check=True,
                    capture_output=True,
                )
            else:
                # Image → video clip with specified duration
                duration = item.effective_duration or 5
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-loop", "1", "-i", str(local_path),
                        "-t", str(duration),
                        "-vf", f"scale={PRESS_WIDTH}:{PRESS_HEIGHT}:force_original_aspect_ratio=decrease,"
                               f"pad={PRESS_WIDTH}:{PRESS_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={PRESS_FPS}",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
                        "-shortest",
                        str(clip_path),
                    ],
                    check=True,
                    capture_output=True,
                )

            clips.append(clip_path)

        # Concatenate clips
        concat_list = tmp / "concat.txt"
        concat_list.write_text("\n".join(f"file '{p}'" for p in clips))

        mp4_out = tmp / "output.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c", "copy",
                str(mp4_out),
            ],
            check=True,
            capture_output=True,
        )

        # Produce HLS
        hls_dir = tmp / "hls"
        hls_dir.mkdir()
        m3u8_path = hls_dir / "playlist.m3u8"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(mp4_out),
                "-c", "copy",
                "-f", "hls",
                "-hls_time", "6",
                "-hls_list_size", "0",
                "-hls_segment_filename", str(hls_dir / "seg%03d.ts"),
                str(m3u8_path),
            ],
            check=True,
            capture_output=True,
        )

        # Poster thumbnail from first frame of output
        poster_path = tmp / "poster.jpg"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", "0", "-i", str(mp4_out),
                "-frames:v", "1",
                str(poster_path),
            ],
            check=True,
            capture_output=True,
        )

        slug = playlist.slug or f"playlist-{playlist.pk}"

        # Save MP4
        playlist.mp4_file.save(
            f"{slug}.mp4",
            ContentFile(mp4_out.read_bytes()),
            save=False,
        )

        # Save HLS manifest (segments are uploaded alongside)
        _upload_hls_segments(playlist, hls_dir, slug)
        playlist.hls_manifest.save(
            f"playlists/hls/{slug}/playlist.m3u8",
            ContentFile(m3u8_path.read_bytes()),
            save=False,
        )

        # Save poster
        playlist.poster.save(
            f"{slug}_poster.jpg",
            ContentFile(poster_path.read_bytes()),
            save=False,
        )

        playlist.status = Playlist.Status.PUBLISHED
        playlist.press_error = ""
        playlist.pressed_at = timezone.now()
        playlist.save()


def _upload_hls_segments(playlist, hls_dir: Path, slug: str) -> None:
    from django.core.files.storage import default_storage

    for segment in hls_dir.glob("*.ts"):
        storage_path = f"playlists/hls/{slug}/{segment.name}"
        if default_storage.exists(storage_path):
            default_storage.delete(storage_path)
        default_storage.save(storage_path, ContentFile(segment.read_bytes()))
