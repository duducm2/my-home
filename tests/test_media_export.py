import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import media_export  # noqa: E402


class MediaExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.webm = media_export.WEBM_MAGIC + b"\x00" * 128

    def test_capabilities_reflect_ffmpeg_availability(self) -> None:
        with patch("media_export.ffmpeg_path", return_value=None):
            result = media_export.capabilities()
        self.assertFalse(result["mp4_available"])
        self.assertEqual(result["fallback_format"], "video/webm")
        with patch("media_export.ffmpeg_path", return_value="ffmpeg"):
            self.assertTrue(media_export.capabilities()["mp4_available"])

    def test_validate_rejects_empty_wrong_type_and_signature(self) -> None:
        with self.assertRaisesRegex(ValueError, "contain data"):
            media_export.validate_webm(b"")
        with self.assertRaisesRegex(ValueError, "WebM format"):
            media_export.validate_webm(self.webm, "video/mp4")
        with self.assertRaisesRegex(ValueError, "signature"):
            media_export.validate_webm(b"not-webm", "video/webm")

    def test_validate_rejects_oversized_input(self) -> None:
        with patch("media_export.MAX_VIDEO_BYTES", 8):
            with self.assertRaisesRegex(ValueError, "80 MB"):
                media_export.validate_webm(media_export.WEBM_MAGIC + b"\x00" * 8)

    def test_command_uses_whatsapp_compatible_h264_settings(self) -> None:
        command = media_export.build_ffmpeg_command(
            "ffmpeg", Path("input.webm"), Path("output.mp4")
        )
        self.assertIn("libx264", command)
        self.assertIn("yuv420p", command)
        self.assertIn("+faststart", command)
        self.assertIn("force_original_aspect_ratio=decrease", " ".join(command))

    def test_conversion_returns_mp4_and_cleans_temporary_files(self) -> None:
        captured: dict[str, Path] = {}

        def successful_runner(command, **kwargs):
            captured["source"] = Path(command[command.index("-i") + 1])
            captured["destination"] = Path(command[-1])
            self.assertTrue(captured["source"].is_file())
            captured["destination"].write_bytes(b"mp4-output")
            return subprocess.CompletedProcess(command, 0, b"", b"")

        result = media_export.convert_webm_to_mp4(
            self.webm,
            executable="ffmpeg",
            runner=successful_runner,
        )
        self.assertEqual(result, b"mp4-output")
        self.assertFalse(captured["source"].parent.exists())

    def test_conversion_preserves_clear_failure_and_unavailable_errors(self) -> None:
        with patch("media_export.ffmpeg_path", return_value=None):
            with self.assertRaises(media_export.FFmpegUnavailable):
                media_export.convert_webm_to_mp4(self.webm)

        def failed_runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, b"", b"codec unavailable")

        with self.assertRaisesRegex(media_export.MediaExportError, "codec unavailable"):
            media_export.convert_webm_to_mp4(
                self.webm,
                executable="ffmpeg",
                runner=failed_runner,
            )


if __name__ == "__main__":
    unittest.main()
