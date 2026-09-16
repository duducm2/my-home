"""Safe, temporary video conversion for 3D scene exports."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable


MAX_VIDEO_BYTES = 80 * 1024 * 1024
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"


class MediaExportError(RuntimeError):
    """Raised when media conversion cannot complete."""


class FFmpegUnavailable(MediaExportError):
    """Raised when FFmpeg is not installed or discoverable."""


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def capabilities() -> dict[str, object]:
    executable = ffmpeg_path()
    return {
        "ok": True,
        "ffmpeg_available": bool(executable),
        "mp4_available": bool(executable),
        "fallback_format": "video/webm",
        "max_video_bytes": MAX_VIDEO_BYTES,
    }


def validate_webm(data: bytes, content_type: str = "") -> None:
    if not isinstance(data, bytes) or not data:
        raise ValueError("video must contain data")
    if len(data) > MAX_VIDEO_BYTES:
        raise ValueError("video exceeds the 80 MB conversion limit")
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_type and normalized_type not in {"video/webm", "application/octet-stream"}:
        raise ValueError("video must use the WebM format")
    if not data.startswith(WEBM_MAGIC):
        raise ValueError("invalid WebM file signature")


def build_ffmpeg_command(executable: str, source: Path, destination: Path) -> list[str]:
    return [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-an",
        "-vf",
        "scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "26",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(destination),
    ]


def convert_webm_to_mp4(
    data: bytes,
    content_type: str = "video/webm",
    *,
    executable: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> bytes:
    validate_webm(data, content_type)
    ffmpeg = executable or ffmpeg_path()
    if not ffmpeg:
        raise FFmpegUnavailable("FFmpeg is not installed; use the WebM fallback")
    with tempfile.TemporaryDirectory(prefix="my-home-media-") as temporary:
        temp_dir = Path(temporary)
        source = temp_dir / "capture.webm"
        destination = temp_dir / "capture.mp4"
        source.write_bytes(data)
        command = build_ffmpeg_command(ffmpeg, source, destination)
        try:
            result = runner(
                command,
                capture_output=True,
                check=False,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MediaExportError("video conversion did not complete") from exc
        if result.returncode != 0 or not destination.is_file():
            stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            message = stderr[-500:] if stderr else "FFmpeg did not create an MP4 file"
            raise MediaExportError(f"video conversion failed: {message}")
        output = destination.read_bytes()
        if not output:
            raise MediaExportError("FFmpeg created an empty MP4 file")
        return output
