"""Atomic persistence for the dashboard notepad."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class NoteStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "general-notes.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({"text": "", "updated_at": now_stamp()})

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"general-notes.json is invalid: {exc}") from exc
            return {
                "ok": True,
                "text": str(payload.get("text") or ""),
                "updated_at": str(payload.get("updated_at") or ""),
            }

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text") or "")
        if len(text) > 100_000:
            raise ValueError("notes cannot exceed 100000 characters")
        with self._lock:
            self._write({"text": text, "updated_at": now_stamp()})
            return self.load()

    def _write(self, payload: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, self.path)
