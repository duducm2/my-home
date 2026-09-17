"""Atomic normalized persistence for unit quotations."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class QuotationStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir.resolve() / "quotations.json"
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write([])

    def _read_document(self) -> dict[str, Any]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"quotations.json is invalid: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(
            document.get("quotations"), list
        ):
            raise ValueError("quotations.json must contain a quotations array")
        return document

    def _write(self, quotations: list[dict[str, Any]]) -> None:
        document = {
            "version": 1,
            "quotations": quotations,
            "updated_at": _stamp(),
        }
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, self.path)

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                dict(item)
                for item in self._read_document()["quotations"]
                if isinstance(item, dict)
            ]

    def for_expense(self, expense_id: str) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in item.items() if key != "expense_id"}
            for item in self.all()
            if str(item.get("expense_id") or "") == expense_id
        ]

    def replace_for_expense(
        self, expense_id: str, quotations: list[dict[str, Any]]
    ) -> None:
        self.replace_many({expense_id: quotations})

    def replace_many(
        self, replacements: dict[str, list[dict[str, Any]]]
    ) -> None:
        with self._lock:
            current = [
                item
                for item in self.all()
                if str(item.get("expense_id") or "") not in replacements
            ]
            for expense_id, quotations in replacements.items():
                current.extend(
                    {"expense_id": expense_id, **dict(item)}
                    for item in quotations
                )
            self._write(current)

    def delete_expense(self, expense_id: str) -> None:
        self.replace_for_expense(expense_id, [])

