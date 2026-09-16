"""Persist house properties + blueprint metadata (JSON in data/)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class HouseStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.json_path = self.data_dir / "house.json"
        self.project_path = self.data_dir / "project.json"
        self.blueprint_path = self.data_dir / "blueprint.jpg"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.json_path.is_file()

    def load(self) -> dict[str, Any]:
        if not self.json_path.is_file():
            return {
                "ok": False,
                "error": "house.json missing",
                "house": None,
                "blueprint_available": self.blueprint_path.is_file(),
            }
        raw = self.json_path.read_text(encoding="utf-8-sig")
        house = json.loads(raw)
        project = None
        if self.project_path.is_file():
            project = json.loads(
                self.project_path.read_text(encoding="utf-8-sig")
            )
        return {
            "ok": True,
            "house": house,
            "project": project,
            "blueprint_available": self.blueprint_path.is_file(),
            "blueprint_url": "/api/house/blueprint.jpg",
        }

    def save(self, house: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(house, dict):
            raise ValueError("house payload must be an object")
        house = dict(house)
        house["updated_at"] = now_stamp()
        # Keep blueprint pointers stable
        blueprint = dict(house.get("blueprint") or {})
        blueprint.setdefault("image_path", "data/blueprint.jpg")
        blueprint.setdefault("image_url", "/api/house/blueprint.jpg")
        house["blueprint"] = blueprint
        self.json_path.write_text(
            json.dumps(house, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return self.load()
