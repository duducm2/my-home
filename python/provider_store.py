"""Atomic JSON persistence for reusable service providers."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from persistence import atomic_write_text

def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class ProviderStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "providers.json"
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({"version": 2, "providers": [], "updated_at": now_stamp()})
        self._migrate_v2()

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
            document["version"] = 2
            document["updated_at"] = now_stamp()
            atomic_write_text(
                self.path,
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                backup=self.path.is_file(),
            )

    @staticmethod
    def _text_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return list(
                dict.fromkeys(str(item).strip() for item in value if str(item).strip())
            )
        text = str(value or "").strip()
        return [text] if text else []

    @staticmethod
    def _contact_list(value: Any) -> list[dict[str, Any]]:
        values = value if isinstance(value, list) else ([value] if value else [])
        result = []
        for index, raw in enumerate(values):
            item = dict(raw) if isinstance(raw, dict) else {"value": str(raw).strip()}
            contact_value = str(item.get("value") or "").strip()
            if not contact_value:
                continue
            result.append(
                {
                    **item,
                    "value": contact_value,
                    "label": str(item.get("label") or "").strip()[:80],
                    "primary": bool(item.get("primary", index == 0)),
                }
            )
        return result

    @classmethod
    def _normalize_v2(cls, item: dict[str, Any]) -> dict[str, Any]:
        roles = cls._text_list(item.get("roles"))
        if not roles:
            roles = cls._text_list(item.get("service_type"))
        phones = cls._contact_list(item.get("phones"))
        emails = cls._contact_list(item.get("emails"))
        websites = cls._contact_list(item.get("websites"))
        legacy_contact = str(item.get("contact") or "").strip()
        if legacy_contact and not phones and not emails:
            if "@" in legacy_contact:
                emails = [{"value": legacy_contact, "label": "", "primary": True}]
            else:
                phones = [{"value": legacy_contact, "label": "", "primary": True}]
        address = item.get("address")
        address = (
            dict(address)
            if isinstance(address, dict)
            else ({"street": str(address).strip()} if str(address or "").strip() else {})
        )
        city = str(item.get("city") or address.get("city") or "").strip()
        state = str(item.get("state") or address.get("state") or "").strip()
        business_scale = str(
            item.get("business_scale") or item.get("scale") or "individual"
        ).strip()
        return {
            **item,
            "roles": roles,
            "scale": business_scale,
            "business_scale": business_scale,
            "coverage": cls._text_list(item.get("coverage")),
            "phones": phones,
            "emails": emails,
            "websites": websites,
            "address": address,
            "city": city,
            "state": state,
            "categories": cls._text_list(item.get("categories")),
            # Compatibility projections for existing clients and contracts.
            "service_type": str(item.get("service_type") or ", ".join(roles)).strip(),
            "contact": legacy_contact
            or (
                str((phones + emails)[0].get("value") or "")
                if (phones + emails)
                else ""
            ),
        }

    def _migrate_v2(self) -> None:
        with self._lock:
            document = self._read()
            migrated = [
                self._normalize_v2(item)
                for item in document["providers"]
                if isinstance(item, dict)
            ]
            if int(document.get("version") or 1) < 2 or migrated != document["providers"]:
                document["providers"] = migrated
                self._write(document)

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
        providers = [self._normalize_v2(item) for item in document["providers"] if include_archived or not item.get("archived")]
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
                **(existing or {}),
                "id": provider_id,
                "name": name,
                "roles": self._text_list(
                    payload.get("roles", payload.get("service_type", (existing or {}).get("roles", [])))
                ),
                "scale": str(
                    payload.get(
                        "business_scale",
                        payload.get(
                            "scale", (existing or {}).get("scale", "individual")
                        ),
                    )
                ).strip(),
                "coverage": self._text_list(payload.get("coverage", (existing or {}).get("coverage", []))),
                "phones": self._contact_list(payload.get("phones", (existing or {}).get("phones", []))),
                "emails": self._contact_list(payload.get("emails", (existing or {}).get("emails", []))),
                "websites": self._contact_list(payload.get("websites", (existing or {}).get("websites", []))),
                "address": (
                    dict(payload.get("address"))
                    if isinstance(payload.get("address"), dict)
                    else {
                        "street": str(
                            payload.get("address")
                            or (
                                (existing or {}).get("address", {}).get("street")
                                if isinstance((existing or {}).get("address"), dict)
                                else (existing or {}).get("address")
                            )
                            or ""
                        ).strip(),
                        "city": str(
                            payload.get("city")
                            or (existing or {}).get("city")
                            or ""
                        ).strip(),
                        "state": str(
                            payload.get("state")
                            or (existing or {}).get("state")
                            or ""
                        ).strip(),
                    }
                ),
                "city": str(
                    payload.get("city") or (existing or {}).get("city") or ""
                ).strip(),
                "state": str(
                    payload.get("state") or (existing or {}).get("state") or ""
                ).strip(),
                "categories": self._text_list(payload.get("categories", (existing or {}).get("categories", []))),
                "service_type": str(payload.get("service_type") or (existing or {}).get("service_type") or "").strip(),
                "contact": str(payload.get("contact") or (existing or {}).get("contact") or "").strip(),
                "notes": str(payload.get("notes") or "").strip(),
                "archived": bool((existing or {}).get("archived", False)),
                "created_at": str((existing or {}).get("created_at") or stamp),
                "updated_at": stamp,
            }
            provider = self._normalize_v2(provider)
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
