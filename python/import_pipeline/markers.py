"""Extract PREVIEW / FILE sections from AI pack text."""

from __future__ import annotations

import re
from typing import Any


_FILE_RE = re.compile(
    r"===FILE:\s*([^\n=]+?)===\s*(.*?)===END_FILE===",
    re.IGNORECASE | re.DOTALL,
)
_PREVIEW_RE = re.compile(
    r"===PREVIEW===\s*(.*?)===END_PREVIEW===",
    re.IGNORECASE | re.DOTALL,
)


def extract_preview(pack_text: str) -> str:
    match = _PREVIEW_RE.search(pack_text or "")
    return (match.group(1).strip() if match else "")


def extract_files(pack_text: str) -> dict[str, str]:
    """Return map of filename -> body (CSV text)."""
    files: dict[str, str] = {}
    for match in _FILE_RE.finditer(pack_text or ""):
        name = match.group(1).strip()
        body = match.group(2).strip()
        # Strip markdown fences if present
        if body.startswith("```"):
            lines = body.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            body = "\n".join(lines).strip()
        files[name] = body
    return files


def materialize_csv(pack_text: str, expected_name: str) -> dict[str, Any]:
    """Find expected FILE section or treat whole body as CSV if it looks like one."""
    files = extract_files(pack_text)
    preview = extract_preview(pack_text)
    if expected_name in files:
        return {"ok": True, "csv_text": files[expected_name], "preview": preview, "files": list(files)}
    # Case-insensitive filename match
    lower = {k.lower(): v for k, v in files.items()}
    if expected_name.lower() in lower:
        return {
            "ok": True,
            "csv_text": lower[expected_name.lower()],
            "preview": preview,
            "files": list(files),
        }
    # Bare CSV fallback (header line present)
    stripped = (pack_text or "").strip()
    if stripped and not stripped.startswith("===") and "," in stripped.splitlines()[0]:
        return {"ok": True, "csv_text": stripped, "preview": preview, "files": []}
    return {
        "ok": False,
        "error": f"missing ===FILE: {expected_name}=== section",
        "preview": preview,
        "files": list(files),
    }
