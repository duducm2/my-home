"""Persist house properties + blueprint metadata (JSON in data/)."""

from __future__ import annotations

import json
import os
import re
import threading
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
        self._lock = threading.RLock()
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
        with self._lock:
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
        with self._lock:
            self._write(house)
        return self.load()

    def _write(self, house: dict[str, Any]) -> None:
        temporary = self.json_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(house, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, self.json_path)

    @staticmethod
    def _number(value: Any, field: str, minimum: float, maximum: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be numeric") from exc
        if number < minimum or number > maximum:
            raise ValueError(f"{field} must be between {minimum} and {maximum}")
        return round(number, 4)

    def _validate_overrides(self, payload: Any, lot_width: float, lot_depth: float) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("layout_overrides must be an object")
        if len(payload) > 300:
            raise ValueError("layout_overrides exceeds 300 elements")
        result: dict[str, Any] = {}
        for key, raw in payload.items():
            if not re.fullmatch(r"(room|wall|zone|fixture|roof):[A-Za-z0-9_:-]{1,100}", str(key)):
                raise ValueError(f"invalid override key: {key}")
            if not isinstance(raw, dict):
                raise ValueError(f"override {key} must be an object")
            translation = raw.get("translation_m") or {}
            scale = raw.get("scale") or {}
            if not isinstance(translation, dict) or not isinstance(scale, dict):
                raise ValueError(f"override {key} has invalid transform")
            result[str(key)] = {
                "translation_m": {
                    "x": self._number(translation.get("x", 0), f"{key}.translation.x", -lot_width, lot_width),
                    "y": self._number(translation.get("y", 0), f"{key}.translation.y", -5, 10),
                    "z": self._number(translation.get("z", 0), f"{key}.translation.z", -lot_depth, lot_depth),
                },
                "rotation_y_deg": self._number(raw.get("rotation_y_deg", 0), f"{key}.rotation", -3600, 3600),
                "scale": {
                    "x": self._number(scale.get("x", 1), f"{key}.scale.x", 0.1, 10),
                    "y": self._number(scale.get("y", 1), f"{key}.scale.y", 0.1, 10),
                    "z": self._number(scale.get("z", 1), f"{key}.scale.z", 0.1, 10),
                },
            }
        return result

    def _validate_assets(self, payload: Any, lot_width: float, lot_depth: float) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            raise ValueError("placed_assets must be an array")
        if len(payload) > 200:
            raise ValueError("placed_assets exceeds 200 elements")
        allowed = {
            "sofa", "bed", "table", "chair", "wardrobe", "refrigerator",
            "stove", "sink", "washer", "cabinet", "plant", "box",
        }
        result = []
        used: set[str] = set()
        for raw in payload:
            if not isinstance(raw, dict):
                raise ValueError("each placed asset must be an object")
            asset_id = str(raw.get("id") or "")
            if not re.fullmatch(r"asset_[A-Za-z0-9_-]{1,64}", asset_id) or asset_id in used:
                raise ValueError(f"invalid or duplicate asset id: {asset_id}")
            used.add(asset_id)
            asset_type = str(raw.get("asset_type") or "")
            if asset_type not in allowed:
                raise ValueError(f"invalid asset_type: {asset_type}")
            color = str(raw.get("color") or "#a88d72")
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                raise ValueError(f"invalid asset color: {color}")
            result.append({
                "id": asset_id,
                "asset_type": asset_type,
                "label": str(raw.get("label") or asset_type)[:80],
                "x_m": self._number(raw.get("x_m"), f"{asset_id}.x_m", 0, lot_width),
                "y_m": self._number(raw.get("y_m", 0), f"{asset_id}.y_m", 0, 10),
                "z_m": self._number(raw.get("z_m"), f"{asset_id}.z_m", 0, lot_depth),
                "width_m": self._number(raw.get("width_m"), f"{asset_id}.width_m", 0.05, 10),
                "height_m": self._number(raw.get("height_m"), f"{asset_id}.height_m", 0.05, 10),
                "depth_m": self._number(raw.get("depth_m"), f"{asset_id}.depth_m", 0.05, 10),
                "rotation_y_deg": self._number(raw.get("rotation_y_deg", 0), f"{asset_id}.rotation", -3600, 3600),
                "color": color,
                "parent_kind": str(raw.get("parent_kind") or "lot")[:32],
                "parent_id": str(raw.get("parent_id") or "")[:80],
                "status": "user_placed",
            })
        return result

    def save_model3d_layout(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("layout payload must be an object")
        with self._lock:
            loaded = self.load()
            if not loaded.get("ok"):
                raise ValueError("house.json missing")
            house = dict(loaded["house"])
            model = dict(house.get("model_3d") or {})
            lot = model.get("lot") or {}
            lot_width = self._number(lot.get("width_m"), "lot.width_m", 1, 1000)
            lot_depth = self._number(lot.get("depth_m"), "lot.depth_m", 1, 1000)
            model["layout_overrides"] = self._validate_overrides(
                payload.get("layout_overrides", {}), lot_width, lot_depth
            )
            model["placed_assets"] = self._validate_assets(
                payload.get("placed_assets", []), lot_width, lot_depth
            )
            model["editor_updated_at"] = now_stamp()
            house["model_3d"] = model
            house["updated_at"] = now_stamp()
            self._write(house)
            return {
                "ok": True,
                "layout_overrides": model["layout_overrides"],
                "placed_assets": model["placed_assets"],
                "updated_at": model["editor_updated_at"],
            }
