"""Atomic persistence for lightweight dashboard tasks."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class QuickTaskStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "quick-tasks.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write([])

    def _read(self) -> list[dict[str, Any]]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"quick-tasks.json is invalid: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(
            document.get("tasks"), list
        ):
            raise ValueError("quick-tasks.json must contain a tasks array")
        return [dict(item) for item in document["tasks"] if isinstance(item, dict)]

    def _write(self, tasks: list[dict[str, Any]]) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {"version": 1, "tasks": tasks, "updated_at": now_stamp()},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, self.path)

    @staticmethod
    def _next_id(tasks: list[dict[str, Any]]) -> str:
        maximum = 0
        for task in tasks:
            task_id = str(task.get("id") or "")
            if task_id.startswith("QUICK_"):
                try:
                    maximum = max(maximum, int(task_id[6:]))
                except ValueError:
                    pass
        return f"QUICK_{maximum + 1:04d}"

    def state(self) -> dict[str, Any]:
        with self._lock:
            tasks = self._read()
            tasks.sort(
                key=lambda item: (
                    bool(item.get("done")),
                    str(item.get("created_at") or ""),
                    str(item.get("id") or ""),
                )
            )
            return {
                "ok": True,
                "tasks": tasks,
                "count": len(tasks),
                "open_count": sum(not bool(item.get("done")) for item in tasks),
            }

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("task title is required")
        if len(title) > 200:
            raise ValueError("task title cannot exceed 200 characters")
        with self._lock:
            tasks = self._read()
            task_id = str(payload.get("id") or "").strip()
            stamp = now_stamp()
            if task_id:
                current = next(
                    (item for item in tasks if str(item.get("id")) == task_id),
                    None,
                )
                if current is None:
                    raise ValueError(f"quick task not found: {task_id}")
                current.update(
                    {
                        "title": title,
                        "done": bool(payload.get("done")),
                        "updated_at": stamp,
                    }
                )
            else:
                task_id = self._next_id(tasks)
                tasks.append(
                    {
                        "id": task_id,
                        "title": title,
                        "done": bool(payload.get("done")),
                        "created_at": stamp,
                        "updated_at": stamp,
                    }
                )
            self._write(tasks)
            return {"task_id": task_id, **self.state()}

    def delete(self, task_id: str) -> dict[str, Any]:
        task_id = str(task_id or "").strip()
        if not task_id:
            raise ValueError("quick task id is required")
        with self._lock:
            tasks = self._read()
            remaining = [
                item for item in tasks if str(item.get("id") or "") != task_id
            ]
            if len(remaining) == len(tasks):
                raise ValueError(f"quick task not found: {task_id}")
            self._write(remaining)
            return {"deleted": task_id, **self.state()}

