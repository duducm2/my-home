"""CSV persistence for home expenses."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


HEADERS = [
    "id",
    "record_type",
    "priority",
    "category",
    "description",
    "icon_key",
    "value",
    "quantity",
    "unit",
    "unit_price",
    "vendor",
    "product_url",
    "price_checked_at",
    "price_notes",
    "provider_id",
    "contract_id",
    "created_at",
    "updated_at",
]


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_value(raw: Any) -> float:
    if raw is None or str(raw).strip() == "":
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"invalid value: {raw!r}") from exc


def _optional_float(raw: Any) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    return _parse_value(raw)


def _priority(raw: Any) -> int:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid priority: {raw!r}") from exc
    if value < 1:
        raise ValueError("priority must be >= 1")
    return value


class ExpenseStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.csv_path = self.data_dir / "expenses.csv"
        self.icon_manifest_path = self.data_dir / "icon-manifest.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.is_file():
            self._write_rows([])
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
        if fieldnames == HEADERS:
            return
        migrated = []
        for row in rows:
            item = {key: row.get(key, "") for key in HEADERS}
            item["record_type"] = item["record_type"] or ("material" if item["category"] == "Material" else "service")
            item["priority"] = item["priority"] or "1"
            item["icon_key"] = item["icon_key"] or self._default_icon_key(item["category"])
            migrated.append(item)
        self._write_rows(migrated)

    def _icon_manifest(self) -> dict[str, Any]:
        if not self.icon_manifest_path.is_file():
            return {"defaults": {}, "icons": {}, "expense_associations": {}}
        try:
            payload = json.loads(self.icon_manifest_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {"defaults": {}, "icons": {}, "expense_associations": {}}
        return payload if isinstance(payload, dict) else {}

    def _load_json_records(self, filename: str, key: str) -> list[dict[str, Any]]:
        path = self.data_dir / filename
        if not path.is_file():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return []
        records = payload.get(key) if isinstance(payload, dict) else []
        return [item for item in records if isinstance(item, dict)] if isinstance(records, list) else []

    def _default_icon_key(self, category: str) -> str:
        defaults = self._icon_manifest().get("defaults") or {}
        name = "material" if category == "Material" else "expense"
        return str(defaults.get(name) or "home-expense")

    def _validated_icon_key(self, icon_key: Any, category: str) -> str:
        key = str(icon_key or "").strip() or self._default_icon_key(category)
        icons = self._icon_manifest().get("icons") or {}
        if icons and key not in icons:
            raise ValueError(f"invalid icon_key: {key}")
        return key

    def _read_rows(self) -> list[dict[str, str]]:
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _write_rows(self, rows: list[dict[str, Any]]) -> None:
        with self.csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in HEADERS})

    @staticmethod
    def _next_id(rows: list[dict[str, str]]) -> str:
        maximum = 0
        for row in rows:
            value = str(row.get("id") or "")
            if value.startswith("EXP_"):
                try:
                    maximum = max(maximum, int(value[4:]))
                except ValueError:
                    pass
        return f"EXP_{maximum + 1:04d}"

    def _normalize(self, row: dict[str, str]) -> dict[str, Any]:
        quantity = _optional_float(row.get("quantity"))
        if quantity is None and row.get("category") == "Material":
            quantity = 1.0
        return {
            "id": row.get("id", ""),
            "record_type": row.get("record_type") or ("material" if row.get("category") == "Material" else "service"),
            "priority": _priority(row.get("priority") or "1"),
            "category": row.get("category", ""),
            "description": row.get("description", ""),
            "icon_key": row.get("icon_key") or self._default_icon_key(row.get("category", "")),
            "value": _parse_value(row.get("value")),
            "quantity": quantity,
            "unit": row.get("unit", ""),
            "unit_price": _optional_float(row.get("unit_price")),
            "vendor": row.get("vendor", ""),
            "product_url": row.get("product_url", ""),
            "price_checked_at": row.get("price_checked_at", ""),
            "price_notes": row.get("price_notes", ""),
            "provider_id": row.get("provider_id", ""),
            "contract_id": row.get("contract_id", ""),
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }

    def list_expenses(self) -> list[dict[str, Any]]:
        expenses = [self._normalize(row) for row in self._read_rows()]
        expenses.sort(
            key=lambda item: (
                item["priority"],
                item["category"].casefold(),
                item["description"].casefold(),
                item["id"],
            )
        )
        return expenses

    @staticmethod
    def _totals(expenses: list[dict[str, Any]]) -> dict[str, Any]:
        by_category: dict[str, float] = {}
        by_priority: dict[str, float] = {}
        materials = services = total = 0.0
        for expense in expenses:
            value = float(expense["value"])
            total += value
            category = expense["category"]
            by_category[category] = by_category.get(category, 0.0) + value
            key = str(expense["priority"])
            by_priority[key] = by_priority.get(key, 0.0) + value
            if expense.get("record_type") == "material":
                materials += value
            else:
                services += value
        return {
            "all": round(total, 2),
            "materials": round(materials, 2),
            "services": round(services, 2),
            "by_category": {key: round(value, 2) for key, value in sorted(by_category.items())},
            "by_priority": {
                key: round(value, 2)
                for key, value in sorted(by_priority.items(), key=lambda item: int(item[0]))
            },
        }

    def state(self) -> dict[str, Any]:
        expenses = self.list_expenses()
        manifest = self._icon_manifest()
        return {
            "ok": True,
            "expenses": expenses,
            "totals": self._totals(expenses),
            "materials": [item for item in expenses if item["record_type"] == "material"],
            "icon_catalog": {
                "defaults": manifest.get("defaults", {}),
                "icons": manifest.get("icons", {}),
            },
        }

    @staticmethod
    def _apply_price_fields(row: dict[str, str], payload: dict[str, Any], stamp: str) -> None:
        if "quantity" in payload and str(payload.get("quantity") or "") != "":
            row["quantity"] = f"{_parse_value(payload['quantity']):g}"
        if "unit" in payload:
            row["unit"] = str(payload.get("unit") or "").strip()
        if "unit_price" in payload and str(payload.get("unit_price") or "") != "":
            row["unit_price"] = f"{_parse_value(payload['unit_price']):.2f}"
        if "vendor" in payload:
            row["vendor"] = str(payload.get("vendor") or "").strip()
        if "product_url" in payload:
            row["product_url"] = str(payload.get("product_url") or "").strip()
        if "price_notes" in payload:
            row["price_notes"] = str(payload.get("price_notes") or "").strip()
        if "price_checked_at" in payload:
            row["price_checked_at"] = str(payload.get("price_checked_at") or "").strip()
        elif any(key in payload for key in ("unit_price", "vendor", "product_url")):
            row["price_checked_at"] = stamp

    def upsert_expense(self, payload: dict[str, Any]) -> dict[str, Any]:
        category = str(payload.get("category") or "").strip()
        description = str(payload.get("description") or "").strip()
        if not category:
            raise ValueError("category is required")
        if not description:
            raise ValueError("description is required")
        priority = _priority(payload.get("priority"))
        value = _parse_value(payload.get("value"))
        record_type = str(payload.get("record_type") or ("material" if category == "Material" else "service")).strip()
        if record_type not in {"material", "service"}:
            raise ValueError("record_type must be material or service")
        provider_id = str(payload.get("provider_id") or "").strip()
        contract_id = str(payload.get("contract_id") or "").strip()
        if record_type == "material" and (provider_id or contract_id):
            raise ValueError("materials cannot be linked to providers or contracts")
        providers = {
            str(item.get("id"))
            for item in self._load_json_records("providers.json", "providers")
            if not item.get("archived")
        }
        contracts = {
            str(item.get("id")): item
            for item in self._load_json_records("contracts.json", "contracts")
            if not item.get("archived")
        }
        if provider_id and provider_id not in providers:
            raise ValueError(f"provider not found: {provider_id}")
        if contract_id:
            contract = contracts.get(contract_id)
            if contract is None or contract.get("type") != "service":
                raise ValueError(f"service contract not found: {contract_id}")
            if provider_id and str(contract.get("provider_id") or "") != provider_id:
                raise ValueError("selected contract belongs to a different provider")
            provider_id = provider_id or str(contract.get("provider_id") or "")
        icon_key = self._validated_icon_key(payload.get("icon_key"), category)
        expense_id = str(payload.get("id") or "").strip()
        stamp = now_stamp()
        rows = self._read_rows()
        if expense_id:
            for row in rows:
                if row.get("id") == expense_id:
                    row.update(
                        {
                            "priority": str(priority),
                            "record_type": record_type,
                            "category": category,
                            "description": description,
                            "icon_key": icon_key,
                            "value": f"{value:.2f}",
                            "provider_id": provider_id,
                            "contract_id": contract_id,
                            "updated_at": stamp,
                        }
                    )
                    self._apply_price_fields(row, payload, stamp)
                    break
            else:
                raise ValueError(f"expense not found: {expense_id}")
        else:
            expense_id = self._next_id(rows)
            row = {key: "" for key in HEADERS}
            row.update(
                {
                    "id": expense_id,
                    "record_type": record_type,
                    "priority": str(priority),
                    "category": category,
                    "description": description,
                    "icon_key": icon_key,
                    "value": f"{value:.2f}",
                    "provider_id": provider_id,
                    "contract_id": contract_id,
                    "quantity": "1" if category == "Material" else "",
                    "created_at": stamp,
                    "updated_at": stamp,
                }
            )
            self._apply_price_fields(row, payload, stamp)
            rows.append(row)
        self._write_rows(rows)
        return {"ok": True, "expense_id": expense_id, "state": self.state()}

    def apply_price_rows(self, price_rows: list[dict[str, Any]]) -> dict[str, Any]:
        rows = self._read_rows()
        by_id = {row["id"]: row for row in rows}
        by_description = {
            row["description"].casefold().strip(): row for row in rows if row.get("category") == "Material"
        }
        updated_ids: list[str] = []
        errors: list[str] = []
        stamp = now_stamp()
        for item in price_rows:
            target = by_id.get(str(item.get("id") or "").strip())
            if target is None:
                target = by_description.get(str(item.get("description") or "").casefold().strip())
            if target is None:
                errors.append(f"no match for {item.get('id') or item.get('description')}")
                continue
            try:
                self._apply_price_fields(target, item, stamp)
                if str(item.get("value") or "") != "":
                    target["value"] = f"{_parse_value(item['value']):.2f}"
                target["updated_at"] = stamp
                updated_ids.append(target["id"])
            except ValueError as exc:
                errors.append(str(exc))
        if updated_ids:
            self._write_rows(rows)
        return {
            "ok": not errors,
            "updated": updated_ids,
            "errors": errors,
            "state": self.state(),
        }

    def delete_expense(self, expense_id: str) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        if not expense_id:
            raise ValueError("id is required")
        rows = self._read_rows()
        remaining = [row for row in rows if row.get("id") != expense_id]
        if len(remaining) == len(rows):
            raise ValueError(f"expense not found: {expense_id}")
        self._write_rows(remaining)
        return {"ok": True, "deleted": expense_id, "state": self.state()}
