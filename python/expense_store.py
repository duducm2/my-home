"""CSV persistence for home expenses."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


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
    "quotations_json",
    "selected_quotation_id",
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
        self._lock = threading.RLock()
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
            if not item["quotations_json"]:
                item["quotations_json"] = "[]"
                if str(item.get("unit_price") or "").strip():
                    quantity = _optional_float(item.get("quantity"))
                    unit_price = _optional_float(item.get("unit_price"))
                    quotation = {
                        "id": "QUOTE_001",
                        "source": "manual",
                        "vendor": str(
                            item.get("vendor") or "Cotação existente"
                        ).strip(),
                        "unit_price": unit_price,
                        "quantity": quantity,
                        "unit": str(item.get("unit") or "").strip(),
                        "shipping_cost": 0.0,
                        "total_price": _parse_value(item.get("value")),
                        "product_url": str(item.get("product_url") or "").strip(),
                        "checked_at": str(item.get("price_checked_at") or "").strip(),
                        "notes": str(item.get("price_notes") or "").strip(),
                    }
                    item["quotations_json"] = json.dumps(
                        [quotation], ensure_ascii=False, separators=(",", ":")
                    )
                    item["selected_quotation_id"] = quotation["id"]
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
        with self._lock:
            with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))

    def _write_rows(self, rows: list[dict[str, Any]]) -> None:
        temporary = self.csv_path.with_suffix(".csv.tmp")
        with self._lock:
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADERS, lineterminator="\n")
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: row.get(key, "") for key in HEADERS})
            os.replace(temporary, self.csv_path)

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

    @staticmethod
    def _quotation_number(
        raw: Any, field: str, *, required: bool = False
    ) -> float | None:
        if raw is None or str(raw).strip() == "":
            if required:
                raise ValueError(f"{field} is required")
            return None
        value = _parse_value(raw)
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{field} must be a finite nonnegative number")
        return round(value, 2)

    def _validate_quotation(
        self,
        payload: dict[str, Any],
        row: dict[str, str],
        quotation_id: str,
        *,
        default_source: str = "manual",
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("quotation must be an object")
        quotation_id = str(quotation_id or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", quotation_id):
            raise ValueError("invalid quotation id")
        source = str(payload.get("source") or default_source).strip().lower()
        if source not in {"manual", "ai"}:
            raise ValueError("quotation source must be manual or ai")
        unit_price = self._quotation_number(
            payload.get("unit_price"), "unit_price", required=True
        )
        quantity = self._quotation_number(payload.get("quantity"), "quantity")
        if quantity is None:
            quantity = self._quotation_number(row.get("quantity"), "quantity")
        if quantity is None:
            quantity = 1.0
        shipping = self._quotation_number(
            payload.get("shipping_cost"), "shipping_cost"
        )
        shipping = 0.0 if shipping is None else shipping
        total = self._quotation_number(payload.get("total_price"), "total_price")
        if total is None:
            total = round(float(unit_price) * quantity + shipping, 2)
        product_url = str(payload.get("product_url") or "").strip()
        if product_url:
            parsed = urlparse(product_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("product_url must be a valid HTTP(S) URL")
        vendor = str(payload.get("vendor") or "").strip()
        if not vendor:
            raise ValueError("vendor is required")
        return {
            "id": quotation_id,
            "source": source,
            "vendor": vendor[:160],
            "unit_price": unit_price,
            "quantity": quantity,
            "unit": str(payload.get("unit") or row.get("unit") or "").strip()[:40],
            "shipping_cost": shipping,
            "total_price": total,
            "product_url": product_url[:1000],
            "checked_at": str(
                payload.get("checked_at")
                or payload.get("price_checked_at")
                or now_stamp()
            ).strip()[:40],
            "notes": str(
                payload.get("notes") or payload.get("price_notes") or ""
            ).strip()[:2000],
        }

    def _parse_quotations(self, row: dict[str, str]) -> list[dict[str, Any]]:
        raw = str(row.get("quotations_json") or "[]").strip() or "[]"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid quotations_json for {row.get('id')}") from exc
        if not isinstance(payload, list) or len(payload) > 5:
            raise ValueError("quotations must be a list with at most 5 items")
        quotations: list[dict[str, Any]] = []
        ids: set[str] = set()
        for index, item in enumerate(payload, start=1):
            quotation_id = str(
                item.get("id") if isinstance(item, dict) else ""
            ).strip() or f"QUOTE_{index:03d}"
            quotation = self._validate_quotation(
                item, row, quotation_id, default_source="manual"
            )
            if quotation_id in ids:
                raise ValueError(f"duplicate quotation id: {quotation_id}")
            ids.add(quotation_id)
            quotations.append(quotation)
        return quotations

    @staticmethod
    def _serialize_quotations(quotations: list[dict[str, Any]]) -> str:
        return json.dumps(quotations, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _next_quotation_id(quotations: list[dict[str, Any]]) -> str:
        maximum = 0
        for quotation in quotations:
            match = re.fullmatch(r"QUOTE_(\d+)", str(quotation.get("id") or ""))
            if match:
                maximum = max(maximum, int(match.group(1)))
        return f"QUOTE_{maximum + 1:03d}"

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
            "quotations": self._parse_quotations(row),
            "selected_quotation_id": row.get("selected_quotation_id", ""),
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

    @staticmethod
    def _project_quotation(row: dict[str, str], quotation: dict[str, Any]) -> None:
        row["unit_price"] = f"{float(quotation['unit_price']):.2f}"
        row["quantity"] = f"{float(quotation['quantity']):g}"
        row["unit"] = str(quotation.get("unit") or "")
        row["vendor"] = str(quotation.get("vendor") or "")
        row["product_url"] = str(quotation.get("product_url") or "")
        row["price_checked_at"] = str(quotation.get("checked_at") or "")
        row["price_notes"] = str(quotation.get("notes") or "")
        row["value"] = f"{float(quotation['total_price']):.2f}"
        row["selected_quotation_id"] = str(quotation["id"])

    @staticmethod
    def _clear_quotation_projection(row: dict[str, str]) -> None:
        for key in (
            "unit_price",
            "vendor",
            "product_url",
            "price_checked_at",
            "price_notes",
            "selected_quotation_id",
        ):
            row[key] = ""

    def _apply_quotation_payload(
        self, row: dict[str, str], payload: dict[str, Any]
    ) -> None:
        if "quotations" not in payload:
            return
        raw = payload.get("quotations")
        if not isinstance(raw, list) or len(raw) > 5:
            raise ValueError("quotations must be a list with at most 5 items")
        quotations: list[dict[str, Any]] = []
        ids: set[str] = set()
        for index, item in enumerate(raw, start=1):
            quotation_id = str(
                item.get("id") if isinstance(item, dict) else ""
            ).strip() or f"QUOTE_{index:03d}"
            if quotation_id in ids:
                raise ValueError(f"duplicate quotation id: {quotation_id}")
            ids.add(quotation_id)
            quotations.append(self._validate_quotation(item, row, quotation_id))
        row["quotations_json"] = self._serialize_quotations(quotations)
        selected_id = str(payload.get("selected_quotation_id") or "").strip()
        if selected_id:
            selected = next(
                (item for item in quotations if item["id"] == selected_id), None
            )
            if selected is None:
                raise ValueError("selected quotation not found")
            self._project_quotation(row, selected)
        else:
            self._clear_quotation_projection(row)

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
                    self._apply_quotation_payload(row, payload)
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
                    "quotations_json": "[]",
                    "provider_id": provider_id,
                    "contract_id": contract_id,
                    "quantity": "1" if category == "Material" else "",
                    "created_at": stamp,
                    "updated_at": stamp,
                }
            )
            self._apply_price_fields(row, payload, stamp)
            self._apply_quotation_payload(row, payload)
            rows.append(row)
        self._write_rows(rows)
        return {"ok": True, "expense_id": expense_id, "state": self.state()}

    @staticmethod
    def _expense_row(
        rows: list[dict[str, str]], expense_id: str
    ) -> dict[str, str]:
        target = next(
            (row for row in rows if row.get("id") == expense_id), None
        )
        if target is None:
            raise ValueError(f"expense not found: {expense_id}")
        return target

    def quotation_state(self, expense_id: str) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        row = self._expense_row(self._read_rows(), expense_id)
        expense = self._normalize(row)
        return {
            "ok": True,
            "expense_id": expense_id,
            "quotations": expense["quotations"],
            "selected_quotation_id": expense["selected_quotation_id"],
            "expense": expense,
        }

    def upsert_quotation(
        self, expense_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        with self._lock:
            rows = self._read_rows()
            row = self._expense_row(rows, expense_id)
            quotations = self._parse_quotations(row)
            quotation_id = str(payload.get("id") or "").strip()
            current = next(
                (item for item in quotations if item["id"] == quotation_id), None
            )
            if current is None:
                if quotation_id:
                    raise ValueError(f"quotation not found: {quotation_id}")
                if len(quotations) >= 5:
                    raise ValueError("an expense can have at most 5 quotations")
                quotation_id = self._next_quotation_id(quotations)
                quotation = self._validate_quotation(
                    payload, row, quotation_id
                )
                quotations.append(quotation)
            else:
                merged = {**current, **payload}
                if "total_price" not in payload:
                    merged.pop("total_price", None)
                quotation = self._validate_quotation(
                    merged,
                    row,
                    quotation_id,
                    default_source=str(current.get("source") or "manual"),
                )
                quotations[quotations.index(current)] = quotation
            row["quotations_json"] = self._serialize_quotations(quotations)
            if (
                row.get("selected_quotation_id") == quotation_id
                or bool(payload.get("selected"))
            ):
                self._project_quotation(row, quotation)
            row["updated_at"] = now_stamp()
            self._write_rows(rows)
        return {
            **self.quotation_state(expense_id),
            "quotation_id": quotation_id,
            "state": self.state(),
        }

    def select_quotation(
        self, expense_id: str, quotation_id: str
    ) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        quotation_id = str(quotation_id or "").strip()
        with self._lock:
            rows = self._read_rows()
            row = self._expense_row(rows, expense_id)
            quotations = self._parse_quotations(row)
            quotation = next(
                (item for item in quotations if item["id"] == quotation_id), None
            )
            if quotation is None:
                raise ValueError(f"quotation not found: {quotation_id}")
            self._project_quotation(row, quotation)
            row["updated_at"] = now_stamp()
            self._write_rows(rows)
        return {**self.quotation_state(expense_id), "state": self.state()}

    def delete_quotation(
        self, expense_id: str, quotation_id: str
    ) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        quotation_id = str(quotation_id or "").strip()
        with self._lock:
            rows = self._read_rows()
            row = self._expense_row(rows, expense_id)
            quotations = self._parse_quotations(row)
            remaining = [
                item for item in quotations if item["id"] != quotation_id
            ]
            if len(remaining) == len(quotations):
                raise ValueError(f"quotation not found: {quotation_id}")
            row["quotations_json"] = self._serialize_quotations(remaining)
            if row.get("selected_quotation_id") == quotation_id:
                self._clear_quotation_projection(row)
            row["updated_at"] = now_stamp()
            self._write_rows(rows)
        return {**self.quotation_state(expense_id), "state": self.state()}

    def apply_price_rows(self, price_rows: list[dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            rows = self._read_rows()
            by_id = {row["id"]: row for row in rows}
            descriptions: dict[str, list[dict[str, str]]] = {}
            for row in rows:
                key = str(row.get("description") or "").casefold().strip()
                if key:
                    descriptions.setdefault(key, []).append(row)
            additions: dict[str, list[dict[str, Any]]] = {}
            errors: list[str] = []
            for item in price_rows:
                provided_id = str(item.get("id") or "").strip()
                target = by_id.get(provided_id) if provided_id else None
                if provided_id and target is None:
                    errors.append(f"no match for {provided_id}")
                    continue
                if target is None:
                    matches = descriptions.get(
                        str(item.get("description") or "").casefold().strip(), []
                    )
                    if len(matches) > 1:
                        errors.append(
                            f"ambiguous description: {item.get('description')}"
                        )
                        continue
                    target = matches[0] if matches else None
                if target is None:
                    errors.append(
                        f"no match for {item.get('id') or item.get('description')}"
                    )
                    continue
                additions.setdefault(target["id"], []).append(item)
            prepared: dict[str, list[dict[str, Any]]] = {}
            selected: dict[str, dict[str, Any]] = {}
            for expense_id, items in additions.items():
                target = by_id[expense_id]
                try:
                    quotations = self._parse_quotations(target)
                    if len(quotations) + len(items) > 5:
                        raise ValueError(
                            f"{expense_id} would exceed the 5 quotation limit"
                        )
                    ids = {item["id"] for item in quotations}
                    for item in items:
                        quotation_id = str(
                            item.get("quotation_id") or ""
                        ).strip() or self._next_quotation_id(quotations)
                        if quotation_id in ids:
                            raise ValueError(
                                f"duplicate quotation id: {quotation_id}"
                            )
                        quotation = self._validate_quotation(
                            {**item, "source": "ai"},
                            target,
                            quotation_id,
                            default_source="ai",
                        )
                        quotations.append(quotation)
                        ids.add(quotation_id)
                        if bool(item.get("selected")):
                            if expense_id in selected:
                                raise ValueError(
                                    f"{expense_id} has multiple selected quotations"
                                )
                            selected[expense_id] = quotation
                    prepared[expense_id] = quotations
                except ValueError as exc:
                    errors.append(str(exc))
            if errors:
                return {
                    "ok": False,
                    "updated": [],
                    "errors": errors,
                    "state": self.state(),
                }
            stamp = now_stamp()
            for expense_id, quotations in prepared.items():
                target = by_id[expense_id]
                target["quotations_json"] = self._serialize_quotations(quotations)
                if expense_id in selected:
                    self._project_quotation(target, selected[expense_id])
                target["updated_at"] = stamp
            updated_ids = list(prepared)
            if updated_ids:
                self._write_rows(rows)
        return {
            "ok": True,
            "updated": updated_ids,
            "errors": [],
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
