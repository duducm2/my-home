"""Persistent selection and vendor outreach planning for quotations."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from persistence import atomic_write_text, timestamp


CAMPAIGN_STATUSES = {
    "draft",
    "ready",
    "contacted",
    "responded",
    "declined",
    "completed",
}


class QuotationPlanningStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "quotation-planning.json"
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write(self._empty())

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "version": 1,
            "selected_category_ids": [],
            "selected_expense_ids": [],
            "campaigns": {},
            "updated_at": timestamp(),
        }

    def _read(self) -> dict[str, Any]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"quotation-planning.json is invalid: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(
            document.get("campaigns"), dict
        ):
            raise ValueError("quotation-planning.json must contain campaigns object")
        return document

    def _write(self, document: dict[str, Any]) -> None:
        payload = dict(document)
        payload["version"] = 1
        payload["updated_at"] = timestamp()
        atomic_write_text(
            self.path,
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            backup=self.path.is_file(),
        )

    def default_message(self, expense: dict[str, Any]) -> str:
        description = str(expense.get("description") or "o item/serviço").strip()
        quantity = expense.get("quantity") or expense.get(
            "default_expected_quantity"
        )
        unit = str(expense.get("unit") or "").strip()
        quantity_text = f" ({quantity:g} {unit})" if isinstance(quantity, (int, float)) else ""
        location = "Nova Odessa/SP"
        house_path = self.data_dir / "house.json"
        if house_path.is_file():
            try:
                address = json.loads(
                    house_path.read_text(encoding="utf-8-sig")
                ).get("address", {})
                city = str(address.get("city") or "").strip()
                state = str(address.get("state") or "").strip()
                location = "/".join(value for value in (city, state) if value) or location
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
        return (
            f"Olá! Gostaria de solicitar uma cotação para {description}{quantity_text}. "
            f"A entrega ou execução será em {location}. Pode informar especificação, "
            "preço unitário e total, frete, disponibilidade, prazo, condições de "
            "pagamento e validade da proposta? Se possível, envie também o link do "
            "produto e a proposta em PDF. Obrigado!"
        )

    @staticmethod
    def _ids(value: Any, field: str) -> list[str]:
        if not isinstance(value, list):
            raise ValueError(f"{field} must be a list")
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    def state(
        self, expenses: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        with self._lock:
            document = self._read()
        campaigns = {
            str(key): dict(value)
            for key, value in document["campaigns"].items()
            if isinstance(value, dict)
        }
        if expenses is not None:
            by_id = {str(item.get("id")): item for item in expenses}
            for expense_id in document.get("selected_expense_ids") or []:
                if expense_id in by_id and expense_id not in campaigns:
                    campaigns[expense_id] = {
                        "expense_id": expense_id,
                        "message": self.default_message(by_id[expense_id]),
                        "vendors": [],
                        "status": "draft",
                        "notes": "",
                    }
        return {
            "ok": True,
            "selected_category_ids": list(
                document.get("selected_category_ids") or []
            ),
            "selected_expense_ids": list(document.get("selected_expense_ids") or []),
            "campaigns": campaigns,
            "statuses": sorted(CAMPAIGN_STATUSES),
            "updated_at": document.get("updated_at", ""),
        }

    def save(
        self, payload: dict[str, Any], expenses: list[dict[str, Any]]
    ) -> dict[str, Any]:
        expense_map = {str(item.get("id")): item for item in expenses}
        with self._lock:
            current = self._read()
            selected_categories = self._ids(
                payload.get(
                    "selected_category_ids",
                    current.get("selected_category_ids", []),
                ),
                "selected_category_ids",
            )
            selected_expenses = self._ids(
                payload.get(
                    "selected_expense_ids", current.get("selected_expense_ids", [])
                ),
                "selected_expense_ids",
            )
            missing = set(selected_expenses) - set(expense_map)
            if missing:
                raise ValueError("expense not found: " + ", ".join(sorted(missing)))
            raw_campaigns = payload.get("campaigns", current.get("campaigns", {}))
            if not isinstance(raw_campaigns, dict):
                raise ValueError("campaigns must be an object keyed by expense id")
            campaigns: dict[str, dict[str, Any]] = {}
            for expense_id, raw in raw_campaigns.items():
                expense_id = str(expense_id).strip()
                if expense_id not in expense_map:
                    raise ValueError(f"expense not found: {expense_id}")
                if not isinstance(raw, dict):
                    raise ValueError(f"campaign {expense_id} must be an object")
                status = str(raw.get("status") or "draft").strip()
                if status not in CAMPAIGN_STATUSES:
                    raise ValueError(f"invalid campaign status: {status}")
                vendors = raw.get("vendors") or []
                if not isinstance(vendors, list):
                    raise ValueError("campaign vendors must be a list")
                normalized_vendors = []
                for vendor in vendors:
                    if not isinstance(vendor, dict):
                        raise ValueError("campaign vendor must be an object")
                    provider_id = str(
                        vendor.get("provider_id") or vendor.get("vendor_id") or ""
                    ).strip()
                    if not provider_id or not re.fullmatch(
                        r"[A-Za-z0-9_-]{1,80}", provider_id
                    ):
                        raise ValueError("campaign vendor provider_id is required")
                    normalized_vendors.append(
                        {
                            **vendor,
                            "provider_id": provider_id,
                            "status": str(vendor.get("status") or "draft")[:40],
                            "contacted_at": str(vendor.get("contacted_at") or "")[:40],
                            "responded_at": str(vendor.get("responded_at") or "")[:40],
                            "notes": str(vendor.get("notes") or "")[:2000],
                        }
                    )
                campaigns[expense_id] = {
                    **raw,
                    "expense_id": expense_id,
                    "message": str(
                        raw.get("message")
                        or self.default_message(expense_map[expense_id])
                    )[:10000],
                    "vendors": normalized_vendors,
                    "status": status,
                    "notes": str(raw.get("notes") or "")[:4000],
                }
            document = {
                **current,
                "selected_category_ids": selected_categories,
                "selected_expense_ids": selected_expenses,
                "campaigns": campaigns,
            }
            self._write(document)
        return self.state(expenses)
