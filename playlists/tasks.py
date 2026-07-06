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

            if media.media_type is None:
                raise ValueError(
                    f'Media item "{media.title}" (id={media.pk}) has not been '
                    "processed yet — thumbnail generation may still be running. "
                    "Wait a moment and try pressing again."
                )

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
                        "ffmpeg", "-nostdin", "-y", "-i", str(local_path),
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
                # Image → video clip with specified duration.
                #
                # We first normalise the source image to a clean, scaled and
                # padded PNG with a single decode, then loop THAT to build the
                # clip. Looping the raw uploaded PNG directly is unreliable:
                # ffmpeg's png_pipe demuxer can reject some perfectly valid
                # PNGs on loop re-reads ("Invalid data found when processing
                # input") and busy-loop forever at ~0 fps. An ffmpeg-produced
                # PNG always loops cleanly.
                duration = item.effective_duration or 5
                clean_image = tmp / f"clean_{index}.png"
                subprocess.run(
                    [
                        "ffmpeg", "-nostdin", "-y",
                        "-i", str(local_path),
                        "-vf", f"scale={PRESS_WIDTH}:{PRESS_HEIGHT}:force_original_aspect_ratio=decrease,"
                               f"pad={PRESS_WIDTH}:{PRESS_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                        "-frames:v", "1",
                        str(clean_image),
                    ],
                    check=True,
                    capture_output=True,
                    stdin=subprocess.DEVNULL,
                )
                subprocess.run(
                    [
                        "ffmpeg", "-nostdin", "-y",
                        "-framerate", str(PRESS_FPS),
                        "-loop", "1", "-t", str(duration), "-i", str(clean_image),
                        "-f", "lavfi", "-t", str(duration),
                        "-i", "anullsrc=r=44100:cl=stereo",
                        "-r", str(PRESS_FPS),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
                        "-pix_fmt", "yuv420p",
                        str(clip_path),
                    ],
                    check=True,
                    capture_output=True,
                    stdin=subprocess.DEVNULL,
                )

            clips.append(clip_path)

        # Concatenate clips
        concat_list = tmp / "concat.txt"
        concat_list.write_text("\n".join(f"file '{p}'" for p in clips))

        mp4_out = tmp / "output.mp4"
        subprocess.run(
            [
                "ffmpeg", "-nostdin", "-y",
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
                "ffmpeg", "-nostdin", "-y", "-i", str(mp4_out),
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
                "ffmpeg", "-nostdin", "-y",
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
        # Pass only "{slug}/playlist.m3u8" — the field's upload_to="playlists/hls/"
        # is prepended automatically, giving playlists/hls/{slug}/playlist.m3u8.
        _upload_hls_segments(playlist, hls_dir, slug)
        playlist.hls_manifest.save(
            f"{slug}/playlist.m3u8",
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
