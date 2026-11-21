"""Atomic persistence for the dashboard credit card expense plan."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


MAX_EXPENSE_IDS = 500


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class CreditCardPlanStore:
    """Persist the list of expense IDs planned for the credit card."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "credit-card-plan.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({"expense_ids": [], "updated_at": now_stamp()})

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"credit-card-plan.json is invalid: {exc}") from exc
            raw_ids = payload.get("expense_ids")
            expense_ids = (
                [str(item).strip() for item in raw_ids if str(item).strip()]
                if isinstance(raw_ids, list)
                else []
            )
            return {
                "ok": True,
                "expense_ids": expense_ids,
                "updated_at": str(payload.get("updated_at") or ""),
            }

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("credit card plan payload must be an object")
        raw_ids = payload.get("expense_ids")
        if raw_ids is None:
            raw_ids = []
        if not isinstance(raw_ids, list):
            raise ValueError("expense_ids must be a list")
        seen: set[str] = set()
        expense_ids: list[str] = []
        for item in raw_ids:
            expense_id = str(item or "").strip()
            if not expense_id or expense_id in seen:
                continue
            seen.add(expense_id)
            expense_ids.append(expense_id)
        if len(expense_ids) > MAX_EXPENSE_IDS:
            raise ValueError(f"expense_ids cannot exceed {MAX_EXPENSE_IDS} items")
        with self._lock:
            self._write({"expense_ids": expense_ids, "updated_at": now_stamp()})
            return self.load()

    def _write(self, payload: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, self.path)
