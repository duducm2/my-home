"""Atomic JSON persistence for reusable service providers."""

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


class ProviderStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "providers.json"
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({"version": 1, "providers": [], "updated_at": now_stamp()})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"providers.json is invalid: {exc}") from exc
            if not isinstance(payload.get("providers"), list):
                raise ValueError("providers.json must contain a providers array")
            return payload

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            document = dict(payload)
            document["version"] = 1
            document["updated_at"] = now_stamp()
            temporary = self.path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            os.replace(temporary, self.path)

    @staticmethod
    def _next_id(providers: list[dict[str, Any]], name: str) -> str:
        slug = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")[:32] or "PROVIDER"
        candidate = f"PROVIDER_{slug}"
        used = {str(item.get("id")) for item in providers}
        suffix = 2
        while candidate in used:
            candidate = f"PROVIDER_{slug}_{suffix}"
            suffix += 1
        return candidate

    def state(self, include_archived: bool = True) -> dict[str, Any]:
        document = self._read()
        providers = [dict(item) for item in document["providers"] if include_archived or not item.get("archived")]
        providers.sort(key=lambda item: (bool(item.get("archived")), str(item.get("name") or "").casefold()))
        return {"ok": True, "providers": providers, "count": len(providers), "updated_at": document.get("updated_at", "")}

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("provider name is required")
        with self._lock:
            document = self._read()
            providers = list(document["providers"])
            provider_id = str(payload.get("id") or "").strip()
            existing: dict[str, Any] | None = None
            index = -1
            if provider_id:
                for index, item in enumerate(providers):
                    if str(item.get("id")) == provider_id:
                        existing = item
                        break
                else:
                    raise ValueError(f"provider not found: {provider_id}")
            else:
                provider_id = self._next_id(providers, name)
            stamp = now_stamp()
            provider = {
                "id": provider_id,
                "name": name,
                "service_type": str(payload.get("service_type") or "").strip(),
                "contact": str(payload.get("contact") or "").strip(),
                "notes": str(payload.get("notes") or "").strip(),
                "archived": bool((existing or {}).get("archived", False)),
                "created_at": str((existing or {}).get("created_at") or stamp),
                "updated_at": stamp,
            }
            if existing is None:
                providers.append(provider)
            else:
                providers[index] = provider
            document["providers"] = providers
            self._write(document)
            return {"ok": True, "provider_id": provider_id, **self.state()}

    def archive(self, provider_id: str) -> dict[str, Any]:
        with self._lock:
            document = self._read()
            for item in document["providers"]:
                if str(item.get("id")) == provider_id:
                    item["archived"] = True
                    item["updated_at"] = now_stamp()
                    break
            else:
                raise ValueError(f"provider not found: {provider_id}")
            self._write(document)
            return {"ok": True, "archived": provider_id, **self.state()}
