"""Atomic JSON persistence and validation for project tasks."""

from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any


STATUSES = {"pending", "in_progress", "blocked", "completed"}


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _positive_int(value: Any, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a positive integer") from exc
    if number < 1:
        raise ValueError(f"{field} must be a positive integer")
    return number


def _iso_date(value: Any, field: str) -> str:
    text = str(value or "").strip()
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD") from exc
    return text


class TaskStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "tasks.json"
        self.expenses_path = self.data_dir / "expenses.csv"
        self.icon_manifest_path = self.data_dir / "icon-manifest.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({"version": 1, "tasks": [], "updated_at": now_stamp()})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"tasks.json is invalid: {exc}") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
                raise ValueError("tasks.json must contain a tasks array")
            return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            payload = dict(payload)
            payload["version"] = 1
            payload["updated_at"] = now_stamp()
            temporary = self.path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            os.replace(temporary, self.path)

    def _expense_ids(self) -> set[str]:
        if not self.expenses_path.is_file():
            return set()
        import csv

        with self.expenses_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return {str(row.get("id") or "") for row in csv.DictReader(handle)}

    def _icon_keys(self) -> set[str]:
        if not self.icon_manifest_path.is_file():
            return set()
        try:
            manifest = json.loads(self.icon_manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return set()
        return set((manifest.get("icons") or {}).keys())

    def _normalize(self, task: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(task.get("id") or ""),
            "title": str(task.get("title") or ""),
            "description": str(task.get("description") or ""),
            "priority": int(task.get("priority") or 1),
            "sequence": int(task.get("sequence") or 1),
            "start_date": str(task.get("start_date") or ""),
            "end_date": str(task.get("end_date") or ""),
            "status": str(task.get("status") or "pending"),
            "expense_id": str(task.get("expense_id") or ""),
            "icon_key": str(task.get("icon_key") or "home-expense"),
            "date_status": str(task.get("date_status") or "confirmed"),
            "source_refs": list(task.get("source_refs") or []),
            "created_at": str(task.get("created_at") or ""),
            "updated_at": str(task.get("updated_at") or ""),
        }

    @staticmethod
    def _sort_key(task: dict[str, Any]) -> tuple[Any, ...]:
        return (
            int(task.get("priority") or 1),
            int(task.get("sequence") or 1),
            str(task.get("start_date") or ""),
            str(task.get("title") or "").casefold(),
            str(task.get("id") or ""),
        )

    def _normalize_sequences(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered = sorted(tasks, key=self._sort_key)
        for sequence, task in enumerate(ordered, start=1):
            task["sequence"] = sequence
        return ordered

    def list_tasks(self) -> list[dict[str, Any]]:
        tasks = [self._normalize(item) for item in self._read()["tasks"]]
        tasks.sort(key=self._sort_key)
        return tasks

    def state(self) -> dict[str, Any]:
        tasks = self.list_tasks()
        return {
            "ok": True,
            "tasks": tasks,
            "statuses": sorted(STATUSES),
            "count": len(tasks),
            "updated_at": self._read().get("updated_at", ""),
        }

    def _validated(self, payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")
        priority = _positive_int(payload.get("priority"), "priority")
        sequence = _positive_int(payload.get("sequence"), "sequence")
        start_date = _iso_date(payload.get("start_date"), "start_date")
        end_date = _iso_date(payload.get("end_date"), "end_date")
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        status = str(payload.get("status") or "pending").strip()
        if status not in STATUSES:
            raise ValueError(f"invalid status: {status}")
        date_status = str(payload.get("date_status") or "confirmed").strip()
        if date_status not in {"estimated", "confirmed"}:
            raise ValueError(f"invalid date_status: {date_status}")
        expense_id = str(payload.get("expense_id") or "").strip()
        if expense_id and expense_id not in self._expense_ids():
            raise ValueError(f"expense not found: {expense_id}")
        icon_key = str(payload.get("icon_key") or "home-expense").strip()
        icon_keys = self._icon_keys()
        if icon_keys and icon_key not in icon_keys:
            raise ValueError(f"invalid icon_key: {icon_key}")
        previous = existing or {}
        stamp = now_stamp()
        return {
            "id": str(previous.get("id") or payload.get("id") or ""),
            "title": title,
            "description": str(payload.get("description") or "").strip(),
            "priority": priority,
            "sequence": sequence,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "expense_id": expense_id,
            "icon_key": icon_key,
            "date_status": date_status,
            "source_refs": list(previous.get("source_refs") or payload.get("source_refs") or []),
            "created_at": str(previous.get("created_at") or stamp),
            "updated_at": stamp,
        }

    @staticmethod
    def _next_id(tasks: list[dict[str, Any]]) -> str:
        maximum = 0
        for task in tasks:
            task_id = str(task.get("id") or "")
            if task_id.startswith("TASK_"):
                try:
                    maximum = max(maximum, int(task_id[5:]))
                except ValueError:
                    pass
        return f"TASK_{maximum + 1:04d}"

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            document = self._read()
            tasks = list(document["tasks"])
            task_id = str(payload.get("id") or "").strip()
            if task_id:
                for index, current in enumerate(tasks):
                    if str(current.get("id")) == task_id:
                        tasks[index] = self._validated(payload, current)
                        break
                else:
                    raise ValueError(f"task not found: {task_id}")
            else:
                item = self._validated(payload)
                item["id"] = self._next_id(tasks)
                tasks.append(item)
                task_id = item["id"]
            document["tasks"] = self._normalize_sequences(tasks)
            self._write(document)
            return {"ok": True, "task_id": task_id, **self.state()}

    def delete(self, task_id: str) -> dict[str, Any]:
        task_id = str(task_id or "").strip()
        if not task_id:
            raise ValueError("task id is required")
        with self._lock:
            document = self._read()
            tasks = [item for item in document["tasks"] if str(item.get("id")) != task_id]
            if len(tasks) == len(document["tasks"]):
                raise ValueError(f"task not found: {task_id}")
            document["tasks"] = self._normalize_sequences(tasks)
            self._write(document)
            return {"ok": True, "deleted": task_id, **self.state()}
