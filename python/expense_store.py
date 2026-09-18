"""CSV persistence for home expenses."""

from __future__ import annotations

import csv
import io
import json
import math
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from quotation_store import QuotationStore
from expense_attachment_store import ExpenseAttachmentStore
from persistence import atomic_write_text, coordinated_write


HEADERS = [
    "id",
    "record_type",
    "category",
    "description",
    "icon_key",
    "unit",
    "default_expected_quantity",
    "selected_quotation_id",
    "baseline_quotation_id",
    "payments_json",
    "provider_id",
    "contract_id",
    "contract_ids_json",
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
        self.legacy_backup_path = self.data_dir / "expenses.pre-allocation.csv"
        self.icon_manifest_path = self.data_dir / "icon-manifest.json"
        self._lock = threading.RLock()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.is_file():
            self._write_rows([])
        self.quotation_store = QuotationStore(self.data_dir)
        self.attachment_store = ExpenseAttachmentStore(self.data_dir)
        self._migrate_schema()
        self._migrate_contract_links()

    def _migrate_contract_links(self) -> None:
        """Reconcile the legacy single contract projection from contract authority."""
        contracts = self._load_json_records("contracts.json", "contracts")
        if not contracts:
            return
        links: dict[str, list[str]] = {}
        providers: dict[str, str] = {}
        for contract in contracts:
            if contract.get("archived"):
                continue
            contract_id = str(contract.get("id") or "")
            provider_id = str(contract.get("provider_id") or "")
            for expense_id in contract.get("expense_ids") or []:
                expense_id = str(expense_id)
                if contract_id:
                    links.setdefault(expense_id, []).append(contract_id)
                if provider_id:
                    providers[expense_id] = provider_id
        rows = self._read_rows()
        changed = False
        for row in rows:
            expense_id = str(row.get("id") or "")
            contract_ids = list(dict.fromkeys(links.get(expense_id, [])))
            serialized = json.dumps(
                contract_ids, ensure_ascii=False, separators=(",", ":")
            )
            primary = contract_ids[0] if contract_ids else ""
            if (
                row.get("contract_ids_json") != serialized
                or row.get("contract_id") != primary
                or (
                    providers.get(expense_id)
                    and row.get("provider_id") != providers[expense_id]
                )
            ):
                row["contract_ids_json"] = serialized
                row["contract_id"] = primary
                if providers.get(expense_id):
                    row["provider_id"] = providers[expense_id]
                changed = True
        if changed:
            self._write_rows(rows)

    def _migrate_schema(self) -> None:
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
        if fieldnames == HEADERS:
            return
        if rows and not self.legacy_backup_path.is_file():
            self.legacy_backup_path.write_bytes(self.csv_path.read_bytes())
        linked_dates, timeline_start, timeline_end = self._task_payment_context()
        migrated = []
        existing_external = {
            str(item.get("expense_id") or "")
            for item in self.quotation_store.all()
        }
        for index, row in enumerate(rows):
            item = {key: row.get(key, "") for key in HEADERS}
            item["record_type"] = item["record_type"] or ("material" if item["category"] == "Material" else "service")
            item["icon_key"] = item["icon_key"] or self._default_icon_key(item["category"])
            quantity = _optional_float(
                row.get("default_expected_quantity", row.get("quantity"))
            )
            item["default_expected_quantity"] = f"{quantity or 1:g}"
            item["unit"] = str(row.get("unit") or "").strip() or "unidade"
            quotations: list[dict[str, Any]] = []
            raw_quotes = str(row.get("quotations_json") or "").strip()
            if raw_quotes:
                try:
                    decoded = json.loads(raw_quotes)
                    if isinstance(decoded, list):
                        quotations = [
                            quote for quote in decoded if isinstance(quote, dict)
                        ]
                except json.JSONDecodeError:
                    quotations = []
            for quotation in quotations:
                try:
                    quoted_quantity = float(quotation.get("quantity") or 1)
                    unit_price = float(quotation.get("unit_price") or 0)
                    total_price = float(quotation.get("total_price") or 0)
                    shipping = float(quotation.get("shipping_cost") or 0)
                except (TypeError, ValueError):
                    continue
                difference = round(
                    total_price - unit_price * quoted_quantity - shipping, 2
                )
                if difference > 0.01:
                    quotation["shipping_cost"] = round(shipping + difference, 2)
                    metadata = quotation.get("metadata")
                    metadata = dict(metadata) if isinstance(metadata, dict) else {}
                    ambiguity = str(metadata.get("ambiguities") or "").strip()
                    note = (
                        "Legacy total exceeded unit arithmetic; difference "
                        "preserved as freight/other cost."
                    )
                    metadata["ambiguities"] = (
                        f"{ambiguity}; {note}".strip("; ") if ambiguity else note
                    )
                    quotation["metadata"] = metadata
            legacy_value = _parse_value(row.get("value"))
            if not quotations and legacy_value > 0:
                unit_price = _optional_float(row.get("unit_price"))
                unit_price = unit_price if unit_price is not None else legacy_value / (quantity or 1)
                quotations = [{
                    "id": "QUOTE_001",
                    "source": "manual",
                    "vendor": str(row.get("vendor") or "Estimativa migrada").strip(),
                    "unit_price": round(unit_price, 2),
                    "quantity": quantity or 1,
                    "unit": item["unit"],
                    "shipping_cost": max(0.0, round(legacy_value - unit_price * (quantity or 1), 2)),
                    "total_price": legacy_value,
                    "product_url": str(row.get("product_url") or "").strip(),
                    "checked_at": str(row.get("price_checked_at") or "").strip() or now_stamp(),
                    "notes": str(row.get("price_notes") or "").strip(),
                    "metadata": {
                        "currency": "BRL",
                        "source_type": "manual",
                        "source_name": "legacy-expense-migration",
                        "ambiguities": "",
                    },
                }]
            if quotations and str(row.get("id") or "") not in existing_external:
                self.quotation_store.replace_for_expense(
                    str(row.get("id") or ""), quotations
                )
            quote_ids = {str(quote.get("id") or "") for quote in quotations}
            selected = str(row.get("selected_quotation_id") or "")
            item["selected_quotation_id"] = selected if selected in quote_ids else ""
            item["baseline_quotation_id"] = str(
                row.get("baseline_quotation_id") or item["selected_quotation_id"]
                or (quotations[0].get("id") if quotations else "")
            )
            if not item["payments_json"]:
                item["payments_json"] = self._serialize_payments(
                    [
                        self._default_payment(
                            item,
                            linked_dates,
                            timeline_start,
                            timeline_end,
                            index,
                            len(rows),
                        )
                    ]
                )
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
        with self._lock:
            handle = io.StringIO(newline="")
            writer = csv.DictWriter(handle, fieldnames=HEADERS, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in HEADERS})
            atomic_write_text(
                self.csv_path, handle.getvalue(), backup=self.csv_path.is_file()
            )

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

    @staticmethod
    def _quotation_metadata(
        payload: dict[str, Any], *, default_source: str
    ) -> dict[str, Any]:
        supplied = payload.get("metadata")
        metadata = dict(supplied) if isinstance(supplied, dict) else {}
        for field in (
            "currency",
            "brand",
            "model",
            "specifications",
            "package_size",
            "availability",
            "seller_location",
            "quote_valid_until",
            "source_type",
            "source_name",
            "source_page",
            "extraction_confidence",
            "ambiguities",
        ):
            if field in payload and field not in metadata:
                metadata[field] = payload[field]
        currency = str(metadata.get("currency") or "BRL").strip().upper()
        if currency != "BRL":
            raise ValueError("quotation currency must be BRL")
        source_type = str(
            metadata.get("source_type")
            or ("manual" if default_source == "manual" else "text")
        ).strip().lower()
        if source_type not in {"text", "pdf", "manual"}:
            raise ValueError("quotation source_type must be text, pdf, or manual")
        valid_until = str(metadata.get("quote_valid_until") or "").strip()
        if valid_until:
            try:
                date.fromisoformat(valid_until)
            except ValueError as exc:
                raise ValueError(
                    "quotation quote_valid_until must be YYYY-MM-DD"
                ) from exc
        source_page_raw = metadata.get("source_page")
        source_page = None
        if source_page_raw is not None and str(source_page_raw).strip():
            try:
                source_page = int(source_page_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("quotation source_page must be an integer") from exc
            if source_page < 1:
                raise ValueError("quotation source_page must be >= 1")
        confidence_raw = metadata.get("extraction_confidence")
        confidence = None
        if confidence_raw is not None and str(confidence_raw).strip():
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "quotation extraction_confidence must be numeric"
                ) from exc
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError(
                    "quotation extraction_confidence must be between 0 and 1"
                )
        result = dict(metadata)
        result.update({
            "currency": currency,
            "source_type": source_type,
            "quote_valid_until": valid_until,
            "source_page": source_page,
            "extraction_confidence": confidence,
        })
        limits = {
            "brand": 160,
            "model": 160,
            "specifications": 2000,
            "package_size": 240,
            "availability": 240,
            "seller_location": 240,
            "source_name": 260,
            "ambiguities": 2000,
        }
        for field, limit in limits.items():
            result[field] = str(metadata.get(field) or "").strip()[:limit]
        return result

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
            quantity = self._quotation_number(
                row.get("default_expected_quantity"), "quantity"
            )
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
        checked_at = str(
            payload.get("checked_at")
            or payload.get("price_checked_at")
            or now_stamp()
        ).strip()[:40]
        try:
            date.fromisoformat(checked_at[:10])
        except ValueError as exc:
            raise ValueError("quotation checked_at must begin with YYYY-MM-DD") from exc
        response_status = str(payload.get("response_status") or "received").strip()
        if response_status not in {
            "draft", "requested", "received", "declined", "expired", "accepted"
        }:
            raise ValueError("invalid quotation response_status")
        received_at = str(
            payload.get("received_at") or payload.get("response_date") or ""
        ).strip()[:40]
        return {
            "id": quotation_id,
            "source": source,
            "provider_id": str(payload.get("provider_id") or "").strip()[:80],
            "vendor": vendor[:160],
            "unit_price": unit_price,
            "quantity": quantity,
            "unit": str(payload.get("unit") or row.get("unit") or "").strip()[:40],
            "shipping_cost": shipping,
            "total_price": total,
            "product_url": product_url[:1000],
            "checked_at": checked_at,
            "notes": str(
                payload.get("notes") or payload.get("price_notes") or ""
            ).strip()[:2000],
            "response_status": response_status,
            "response_channel": str(payload.get("response_channel") or "").strip()[:80],
            "received_at": received_at,
            "response_date": received_at,
            "validity": str(payload.get("validity") or "").strip()[:500],
            "references": list(payload.get("references") or [])
            if isinstance(payload.get("references"), list)
            else [],
            "archived": bool(payload.get("archived", False)),
            "attachments": list(payload.get("attachments") or [])
            if isinstance(payload.get("attachments"), list)
            else [],
            "vendor_snapshot": dict(payload.get("vendor_snapshot") or {})
            if isinstance(payload.get("vendor_snapshot"), dict)
            else {},
            "metadata": self._quotation_metadata(
                payload, default_source=default_source
            ),
        }

    def _parse_quotations(self, row: dict[str, str]) -> list[dict[str, Any]]:
        payload = self.quotation_store.for_expense(str(row.get("id") or ""))
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

    def _store_quotations(
        self, row: dict[str, str], quotations: list[dict[str, Any]]
    ) -> None:
        self.quotation_store.replace_for_expense(
            str(row.get("id") or ""), quotations
        )

    @staticmethod
    def _next_quotation_id(quotations: list[dict[str, Any]]) -> str:
        maximum = 0
        for quotation in quotations:
            match = re.fullmatch(r"QUOTE_(\d+)", str(quotation.get("id") or ""))
            if match:
                maximum = max(maximum, int(match.group(1)))
        return f"QUOTE_{maximum + 1:03d}"

    def _task_payment_context(
        self,
    ) -> tuple[dict[str, str], date, date]:
        task_path = self.data_dir / "tasks.json"
        tasks: list[dict[str, Any]] = []
        if task_path.is_file():
            try:
                document = json.loads(task_path.read_text(encoding="utf-8-sig"))
                raw_tasks = document.get("tasks", []) if isinstance(document, dict) else []
                tasks = [item for item in raw_tasks if isinstance(item, dict)]
            except (OSError, json.JSONDecodeError):
                tasks = []
        valid_dates = []
        linked: dict[str, str] = {}
        for task in tasks:
            try:
                task_date = date.fromisoformat(str(task.get("start_date") or ""))
            except ValueError:
                continue
            valid_dates.append(task_date)
            expense_id = str(task.get("expense_id") or "").strip()
            if expense_id and (
                expense_id not in linked or task_date.isoformat() < linked[expense_id]
            ):
                linked[expense_id] = task_date.isoformat()
        start = min(valid_dates, default=date.today())
        end = max(valid_dates, default=start + timedelta(days=365))
        if end <= start:
            end = start + timedelta(days=365)
        return linked, start, end

    @staticmethod
    def _default_payment(
        row: dict[str, Any],
        linked_dates: dict[str, str],
        timeline_start: date,
        timeline_end: date,
        index: int,
        total_rows: int,
    ) -> dict[str, Any]:
        expense_id = str(row.get("id") or "")
        linked_date = linked_dates.get(expense_id)
        if linked_date:
            payment_date = linked_date
            source = "task_start"
        else:
            span = max(1, (timeline_end - timeline_start).days)
            ratio = (index + 0.5) / max(1, total_rows)
            priority_offset = (max(1, _priority(row.get("priority") or 1)) - 1) * 7
            offset = min(span, round(span * ratio) + priority_offset)
            payment_date = (timeline_start + timedelta(days=offset)).isoformat()
            source = "presumed"
        return {
            "id": "PAY_001",
            "date": payment_date,
            "amount": round(_parse_value(row.get("value")), 2),
            "date_status": "estimated",
            "source": source,
            "notes": "",
        }

    @staticmethod
    def _serialize_payments(payments: list[dict[str, Any]]) -> str:
        return json.dumps(payments, ensure_ascii=False, separators=(",", ":"))

    def _parse_payments(self, row: dict[str, str]) -> list[dict[str, Any]]:
        raw = str(row.get("payments_json") or "[]").strip() or "[]"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid payments_json for {row.get('id')}") from exc
        if not isinstance(payload, list):
            raise ValueError(f"invalid payments_json for {row.get('id')}")
        return payload

    @staticmethod
    def _validate_payments(
        payload: Any, value: float | None = None
    ) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or not payload or len(payload) > 36:
            raise ValueError("payments must contain between 1 and 36 items")
        result: list[dict[str, Any]] = []
        ids: set[str] = set()
        for index, raw in enumerate(payload, start=1):
            if not isinstance(raw, dict):
                raise ValueError("each payment must be an object")
            payment_id = str(raw.get("id") or f"PAY_{index:03d}").strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", payment_id):
                raise ValueError(f"invalid payment id: {payment_id}")
            if payment_id in ids:
                raise ValueError(f"duplicate payment id: {payment_id}")
            ids.add(payment_id)
            payment_date = str(raw.get("date") or "").strip()
            try:
                date.fromisoformat(payment_date)
            except ValueError as exc:
                raise ValueError("payment date must use YYYY-MM-DD") from exc
            amount = round(_parse_value(raw.get("amount")), 2)
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("payment amount must be a finite nonnegative number")
            date_status = str(raw.get("date_status") or "confirmed").strip()
            if date_status not in {"estimated", "confirmed"}:
                raise ValueError("payment date_status must be estimated or confirmed")
            result.append(
                {
                    "id": payment_id,
                    "date": payment_date,
                    "amount": amount,
                    "date_status": date_status,
                    "source": str(raw.get("source") or "manual").strip()[:40],
                    "notes": str(raw.get("notes") or "").strip()[:500],
                }
            )
        result.sort(key=lambda item: (item["date"], item["id"]))
        return result

    def _sync_payment_total(self, row: dict[str, str]) -> None:
        # Quotation selection no longer mutates confirmed payment schedules.
        return

    def _allocation_context(self) -> dict[str, list[dict[str, Any]]]:
        tasks_path = self.data_dir / "tasks.json"
        if not tasks_path.is_file():
            return {}
        try:
            document = json.loads(tasks_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {}
        result: dict[str, list[dict[str, Any]]] = {}
        for task in document.get("tasks", []):
            if not isinstance(task, dict) or task.get("activity_type") == "macro":
                continue
            allocations = task.get("expense_allocations")
            if not isinstance(allocations, list):
                legacy_id = str(task.get("expense_id") or "").strip()
                allocations = (
                    [{"expense_id": legacy_id, "expected_quantity": 1}]
                    if legacy_id
                    else []
                )
            for allocation in allocations:
                if not isinstance(allocation, dict):
                    continue
                expense_id = str(allocation.get("expense_id") or "").strip()
                try:
                    quantity = float(allocation.get("expected_quantity") or 0)
                except (TypeError, ValueError):
                    continue
                if expense_id and quantity > 0:
                    result.setdefault(expense_id, []).append(
                        {
                            "task_id": str(task.get("id") or ""),
                            "task_title": str(task.get("title") or ""),
                            "date": str(task.get("start_date") or ""),
                            "date_status": str(
                                task.get("date_status") or "estimated"
                            ),
                            "expected_quantity": quantity,
                        }
                    )
        return result

    @staticmethod
    def _quotation_cost(quotation: dict[str, Any], quantity: float) -> float:
        return round(
            float(quotation.get("unit_price") or 0) * quantity
            + float(quotation.get("shipping_cost") or 0),
            2,
        )

    @staticmethod
    def _median_unit_price(quotations: list[dict[str, Any]]) -> float | None:
        prices = [
            float(quote["unit_price"])
            for quote in quotations
            if not quote.get("archived")
            and quote.get("unit_price") is not None
            and math.isfinite(float(quote.get("unit_price") or 0))
        ]
        if not prices:
            return None
        ordered = sorted(prices)
        mid = len(ordered) // 2
        if len(ordered) % 2:
            return round(ordered[mid], 4)
        return round((ordered[mid - 1] + ordered[mid]) / 2, 4)

    def _scenario(
        self,
        row: dict[str, str],
        quotations: list[dict[str, Any]],
        allocations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        default_quantity = _parse_value(
            row.get("default_expected_quantity") or 1
        )
        quantity = (
            sum(float(item["expected_quantity"]) for item in allocations)
            if allocations
            else default_quantity
        )
        active_quotations = [
            quote
            for quote in quotations
            if not quote.get("archived")
            and quote.get("response_status") in {"received", "accepted"}
        ]
        selected_id = str(row.get("selected_quotation_id") or "")
        baseline_id = str(row.get("baseline_quotation_id") or "")
        selected = next(
            (quote for quote in active_quotations if quote["id"] == selected_id),
            None,
        )
        baseline = next(
            (quote for quote in active_quotations if quote["id"] == baseline_id),
            None,
        )
        planned_quote = selected or baseline
        ranked = sorted(
            active_quotations,
            key=lambda quote: self._quotation_cost(quote, quantity),
        )
        return {
            "expected_quantity": round(quantity, 4),
            "quantity_source": "allocations" if allocations else "expense_default",
            "planned": (
                self._quotation_cost(planned_quote, quantity)
                if planned_quote
                else None
            ),
            "minimum": (
                self._quotation_cost(ranked[0], quantity) if ranked else None
            ),
            "maximum": (
                self._quotation_cost(ranked[-1], quantity) if ranked else None
            ),
            "planned_quotation_id": (
                str(planned_quote.get("id") or "") if planned_quote else ""
            ),
            "minimum_quotation_id": (
                str(ranked[0].get("id") or "") if ranked else ""
            ),
            "maximum_quotation_id": (
                str(ranked[-1].get("id") or "") if ranked else ""
            ),
            "unpriced": planned_quote is None,
        }

    def _projected_payments(
        self,
        row: dict[str, str],
        scenario: dict[str, Any],
        quotations: list[dict[str, Any]],
        allocations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        persisted = self._parse_payments(row)
        confirmed = [
            payment
            for payment in persisted
            if payment.get("date_status") == "confirmed"
        ]
        if confirmed:
            return confirmed
        quote = next(
            (
                item
                for item in quotations
                if item["id"] == scenario["planned_quotation_id"]
            ),
            None,
        )
        if quote and allocations:
            ordered = sorted(
                allocations, key=lambda item: (item.get("date") or "", item["task_id"])
            )
            payments = []
            for index, allocation in enumerate(ordered, start=1):
                amount = float(quote["unit_price"]) * float(
                    allocation["expected_quantity"]
                )
                if index == 1:
                    amount += float(quote.get("shipping_cost") or 0)
                payments.append(
                    {
                        "id": f"ALLOC_{allocation['task_id']}",
                        "date": allocation["date"],
                        "amount": round(amount, 2),
                        "date_status": allocation["date_status"],
                        "source": "activity_allocation",
                        "task_id": allocation["task_id"],
                        "notes": allocation["task_title"],
                    }
                )
            return payments
        if scenario["planned"] is not None:
            payment_date = (
                str(persisted[0].get("date") or "") if persisted else date.today().isoformat()
            )
            return [{
                "id": "PAY_PROJECTED",
                "date": payment_date,
                "amount": scenario["planned"],
                "date_status": "estimated",
                "source": "expense_default",
                "notes": "",
            }]
        return []

    def _normalize(
        self,
        row: dict[str, str],
        allocation_context: dict[str, list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        quotations = self._parse_quotations(row)
        allocations = (allocation_context or self._allocation_context()).get(
            str(row.get("id") or ""), []
        )
        scenario = self._scenario(row, quotations, allocations)
        planned_quote = next(
            (
                quote
                for quote in quotations
                if quote["id"] == scenario["planned_quotation_id"]
            ),
            None,
        )
        try:
            contract_ids = json.loads(row.get("contract_ids_json") or "[]")
        except json.JSONDecodeError:
            contract_ids = []
        if not isinstance(contract_ids, list):
            contract_ids = []
        legacy_contract_id = str(row.get("contract_id") or "")
        contract_ids = list(
            dict.fromkeys(
                [
                    *(str(value) for value in contract_ids if str(value)),
                    *([legacy_contract_id] if legacy_contract_id else []),
                ]
            )
        )
        record_type = row.get("record_type") or (
            "material" if row.get("category") == "Material" else "service"
        )
        median_unit_price = self._median_unit_price(quotations)
        quantity = scenario["expected_quantity"]
        planned = float(scenario["planned"] or 0.0)
        if record_type == "material":
            forecast_total = (
                round(float(median_unit_price) * float(quantity or 0), 2)
                if median_unit_price is not None
                else round(planned, 2)
            )
        else:
            forecast_total = round(planned, 2)
        return {
            "id": row.get("id", ""),
            "record_type": record_type,
            "category": row.get("category", ""),
            "description": row.get("description", ""),
            "icon_key": row.get("icon_key") or self._default_icon_key(row.get("category", "")),
            "value": planned,
            "payments": self._projected_payments(
                row, scenario, quotations, allocations
            ),
            "quantity": quantity,
            "default_expected_quantity": _parse_value(
                row.get("default_expected_quantity") or 1
            ),
            "unit": row.get("unit", ""),
            "unit_price": (
                float(planned_quote["unit_price"]) if planned_quote else None
            ),
            "median_unit_price": median_unit_price,
            "forecast_total": forecast_total,
            "vendor": str((planned_quote or {}).get("vendor") or ""),
            "product_url": str((planned_quote or {}).get("product_url") or ""),
            "price_checked_at": str((planned_quote or {}).get("checked_at") or ""),
            "price_notes": str((planned_quote or {}).get("notes") or ""),
            "quotations": quotations,
            "selected_quotation_id": row.get("selected_quotation_id", ""),
            "baseline_quotation_id": row.get("baseline_quotation_id", ""),
            "scenario": scenario,
            "expense_allocations": allocations,
            "provider_id": row.get("provider_id", ""),
            "contract_id": row.get("contract_id", ""),
            "contract_ids": contract_ids,
            "attachments": self.attachment_store.for_expense(str(row.get("id") or "")),
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }

    def list_expenses(self) -> list[dict[str, Any]]:
        allocation_context = self._allocation_context()
        expenses = [
            self._normalize(row, allocation_context) for row in self._read_rows()
        ]
        expenses.sort(
            key=lambda item: (
                item["category"].casefold(),
                item["description"].casefold(),
                item["id"],
            )
        )
        return expenses

    @staticmethod
    def _totals(expenses: list[dict[str, Any]]) -> dict[str, Any]:
        by_category: dict[str, float] = {}
        by_category_scenarios: dict[str, dict[str, float]] = {}
        materials = services = total = minimum = maximum = 0.0
        forecast_materials = forecast_services = 0.0
        unpriced = 0
        for expense in expenses:
            value = float(expense["value"])
            total += value
            minimum += float(expense["scenario"]["minimum"] or 0)
            maximum += float(expense["scenario"]["maximum"] or 0)
            unpriced += int(expense["scenario"]["unpriced"])
            category = expense["category"]
            by_category[category] = by_category.get(category, 0.0) + value
            scenarios = by_category_scenarios.setdefault(
                category, {"planned": 0.0, "minimum": 0.0, "maximum": 0.0}
            )
            scenarios["planned"] += value
            scenarios["minimum"] += float(expense["scenario"]["minimum"] or 0)
            scenarios["maximum"] += float(expense["scenario"]["maximum"] or 0)
            forecast_value = float(expense.get("forecast_total") or 0)
            if expense.get("record_type") == "material":
                materials += value
                forecast_materials += forecast_value
            else:
                services += value
                forecast_services += forecast_value
        return {
            "all": round(total, 2),
            "materials": round(materials, 2),
            "services": round(services, 2),
            "forecast_all": round(forecast_materials + forecast_services, 2),
            "forecast_materials": round(forecast_materials, 2),
            "forecast_services": round(forecast_services, 2),
            "by_category": {key: round(value, 2) for key, value in sorted(by_category.items())},
            "scenarios": {
                "planned": round(total, 2),
                "minimum": round(minimum, 2),
                "maximum": round(maximum, 2),
                "unpriced_count": unpriced,
            },
            "by_category_scenarios": {
                key: {name: round(amount, 2) for name, amount in values.items()}
                for key, values in sorted(by_category_scenarios.items())
            },
        }

    def _load_budget_forecast(self) -> dict[str, Any] | None:
        path = self.data_dir / "budget-forecast.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def state(self) -> dict[str, Any]:
        expenses = self.list_expenses()
        manifest = self._icon_manifest()
        return {
            "ok": True,
            "expenses": expenses,
            "totals": self._totals(expenses),
            "materials": [item for item in expenses if item["record_type"] == "material"],
            "budget_forecast": self._load_budget_forecast(),
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
        row["selected_quotation_id"] = str(quotation["id"])

    @staticmethod
    def _clear_quotation_projection(row: dict[str, str]) -> None:
        row["selected_quotation_id"] = ""

    def _apply_quotation_payload(
        self, row: dict[str, str], payload: dict[str, Any]
    ) -> None:
        if "quotations" not in payload:
            return
        raw = payload.get("quotations")
        if not isinstance(raw, list):
            raise ValueError("quotations must be a list")
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
        self._store_quotations(row, quotations)

    def _apply_payment_payload(
        self,
        row: dict[str, str],
        payload: dict[str, Any],
        row_index: int,
        total_rows: int,
    ) -> None:
        if "payments" in payload:
            payments = self._validate_payments(payload.get("payments"))
            row["payments_json"] = self._serialize_payments(payments)
            return
        if str(row.get("payments_json") or "").strip():
            return
        linked_dates, timeline_start, timeline_end = self._task_payment_context()
        row["payments_json"] = self._serialize_payments(
            [
                self._default_payment(
                    row,
                    linked_dates,
                    timeline_start,
                    timeline_end,
                    row_index,
                    max(1, total_rows),
                )
            ]
        )

    def upsert_expense(self, payload: dict[str, Any]) -> dict[str, Any]:
        category = str(payload.get("category") or "").strip()
        description = str(payload.get("description") or "").strip()
        if not category:
            raise ValueError("category is required")
        if not description:
            raise ValueError("description is required")
        unit = str(payload.get("unit") or "").strip()
        if not unit:
            raise ValueError("unit is required")
        default_quantity = _parse_value(
            payload.get(
                "default_expected_quantity",
                payload.get("quantity") if "quantity" in payload else 1,
            )
        )
        if not math.isfinite(default_quantity) or default_quantity <= 0:
            raise ValueError(
                "default_expected_quantity must be a finite positive number"
            )
        record_type = str(payload.get("record_type") or ("material" if category == "Material" else "service")).strip()
        if record_type not in {"material", "service"}:
            raise ValueError("record_type must be material or service")
        provider_id = str(payload.get("provider_id") or "").strip()
        raw_contract_ids = payload.get("contract_ids")
        contract_ids = (
            list(dict.fromkeys(str(value).strip() for value in raw_contract_ids if str(value).strip()))
            if isinstance(raw_contract_ids, list)
            else []
        )
        contract_id = str(payload.get("contract_id") or "").strip()
        if contract_id and contract_id not in contract_ids:
            contract_ids.insert(0, contract_id)
        if record_type == "material" and (provider_id or contract_ids):
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
        for linked_contract_id in contract_ids:
            contract = contracts.get(linked_contract_id)
            if contract is None or contract.get("type") != "service":
                raise ValueError(f"service contract not found: {linked_contract_id}")
            if provider_id and str(contract.get("provider_id") or "") != provider_id:
                raise ValueError("selected contracts belong to a different provider")
            provider_id = provider_id or str(contract.get("provider_id") or "")
        contract_id = contract_ids[0] if contract_ids else ""
        icon_key = self._validated_icon_key(payload.get("icon_key"), category)
        expense_id = str(payload.get("id") or "").strip()
        stamp = now_stamp()
        rows = self._read_rows()
        if expense_id:
            for row_index, row in enumerate(rows):
                if row.get("id") == expense_id:
                    row.update(
                        {
                            "record_type": record_type,
                            "category": category,
                            "description": description,
                            "icon_key": icon_key,
                            "unit": unit,
                            "default_expected_quantity": f"{default_quantity:g}",
                            "provider_id": provider_id,
                            "contract_id": contract_id,
                            "contract_ids_json": json.dumps(
                                contract_ids, ensure_ascii=False, separators=(",", ":")
                            ),
                            "updated_at": stamp,
                        }
                    )
                    self._apply_payment_payload(
                        row, payload, row_index, len(rows)
                    )
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
                    "category": category,
                    "description": description,
                    "icon_key": icon_key,
                    "unit": unit,
                    "default_expected_quantity": f"{default_quantity:g}",
                    "provider_id": provider_id,
                    "contract_id": contract_id,
                    "contract_ids_json": json.dumps(
                        contract_ids, ensure_ascii=False, separators=(",", ":")
                    ),
                    "payments_json": "[]",
                    "created_at": stamp,
                    "updated_at": stamp,
                }
            )
            self._apply_payment_payload(
                row, payload, len(rows), len(rows) + 1
            )
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
            if (
                not row.get("baseline_quotation_id")
                and not quotation.get("archived")
                and quotation.get("response_status") in {"received", "accepted"}
            ):
                row["baseline_quotation_id"] = quotation_id
            with coordinated_write([self.quotation_store.path, self.csv_path]):
                self._store_quotations(row, quotations)
                if (
                    row.get("selected_quotation_id") == quotation_id
                    or bool(payload.get("selected"))
                ):
                    self._project_quotation(row, quotation)
                    self._sync_payment_total(row)
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
            if quotation.get("archived") or quotation.get(
                "response_status"
            ) not in {"received", "accepted"}:
                raise ValueError(
                    "only active received quotations can be selected"
                )
            self._project_quotation(row, quotation)
            self._sync_payment_total(row)
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
            remaining = [item for item in quotations if item["id"] != quotation_id]
            if len(remaining) == len(quotations):
                raise ValueError(f"quotation not found: {quotation_id}")
            with coordinated_write([self.quotation_store.path, self.csv_path]):
                self.quotation_store.archive(expense_id, quotation_id)
                if row.get("selected_quotation_id") == quotation_id:
                    self._clear_quotation_projection(row)
                if row.get("baseline_quotation_id") == quotation_id:
                    row["baseline_quotation_id"] = (
                        str(remaining[0].get("id") or "") if remaining else ""
                    )
                row["updated_at"] = now_stamp()
                self._write_rows(rows)
        return {**self.quotation_state(expense_id), "state": self.state()}

    def apply_price_rows(
        self,
        price_rows: list[dict[str, Any]],
        *,
        preserve_financial_state: bool = False,
    ) -> dict[str, Any]:
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
                    ids = {item["id"] for item in quotations}
                    for item in items:
                        quotation_id = str(
                            item.get("quotation_id") or ""
                        ).strip() or self._next_quotation_id(quotations)
                        existing = next(
                            (
                                quotation
                                for quotation in quotations
                                if quotation["id"] == quotation_id
                            ),
                            None,
                        )
                        merged = (
                            {**existing, **item, "source": "ai"}
                            if existing
                            else {**item, "source": "ai"}
                        )
                        quotation = self._validate_quotation(
                            merged, target, quotation_id, default_source="ai"
                        )
                        if existing:
                            quotations[quotations.index(existing)] = quotation
                        else:
                            quotations.append(quotation)
                            ids.add(quotation_id)
                        if bool(item.get("selected")) and not preserve_financial_state:
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
                if (
                    not preserve_financial_state
                    and not target.get("baseline_quotation_id")
                    and quotations
                ):
                    target["baseline_quotation_id"] = str(
                        quotations[0].get("id") or ""
                    )
                if expense_id in selected:
                    self._project_quotation(target, selected[expense_id])
                    self._sync_payment_total(target)
                target["updated_at"] = stamp
            updated_ids = list(prepared)
            if updated_ids:
                with coordinated_write(
                    [self.quotation_store.path, self.csv_path]
                ):
                    self.quotation_store.replace_many(prepared)
                    self._write_rows(rows)
        return {
            "ok": True,
            "updated": updated_ids,
            "errors": [],
            "state": self.state(),
        }

    def sync_task_payment_date(
        self, expense_id: Any, start_date: Any
    ) -> dict[str, Any] | None:
        expense_id = str(expense_id or "").strip()
        start_date = str(start_date or "").strip()
        if not expense_id:
            return None
        try:
            date.fromisoformat(start_date)
        except ValueError as exc:
            raise ValueError("task start_date must use YYYY-MM-DD") from exc
        with self._lock:
            rows = self._read_rows()
            row = self._expense_row(rows, expense_id)
            payments = self._parse_payments(row)
            linked = [
                payment
                for payment in payments
                if payment.get("source") == "task_start"
                and payment.get("date_status") == "estimated"
            ]
            if (
                not linked
                and len(payments) == 1
                and payments[0].get("source") == "presumed"
                and payments[0].get("date_status") == "estimated"
            ):
                linked = payments
                linked[0]["source"] = "task_start"
            if not linked:
                return self.state()
            for payment in linked:
                payment["date"] = start_date
            payments.sort(key=lambda item: (item["date"], item["id"]))
            row["payments_json"] = self._serialize_payments(payments)
            row["updated_at"] = now_stamp()
            self._write_rows(rows)
        return self.state()

    def delete_expense(self, expense_id: str) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        if not expense_id:
            raise ValueError("id is required")
        if self._allocation_context().get(expense_id):
            raise ValueError(
                "expense is linked to activities; remove allocations first"
            )
        rows = self._read_rows()
        remaining = [row for row in rows if row.get("id") != expense_id]
        if len(remaining) == len(rows):
            raise ValueError(f"expense not found: {expense_id}")
        with coordinated_write(
            [
                self.csv_path,
                self.quotation_store.path,
                self.attachment_store.path,
            ]
        ):
            self._write_rows(remaining)
            self.quotation_store.delete_expense(expense_id)
            self.attachment_store.delete_expense(expense_id)
        return {"ok": True, "deleted": expense_id, "state": self.state()}

    def _known_expense_ids(self) -> set[str]:
        return {str(row.get("id") or "") for row in self._read_rows() if row.get("id")}

    def add_expense_document(
        self, expense_id: str, data: bytes, original_filename: str
    ) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        attachment = self.attachment_store.add_upload(
            expense_id,
            data,
            original_filename,
            expense_ids=self._known_expense_ids(),
        )
        return {
            "ok": True,
            "expense_id": expense_id,
            "document": attachment,
            "state": self.state(),
        }

    def link_expense_system_document(
        self, expense_id: str, system_document_id: str
    ) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        attachment = self.attachment_store.attach_system_document(
            expense_id,
            system_document_id,
            expense_ids=self._known_expense_ids(),
        )
        return {
            "ok": True,
            "expense_id": expense_id,
            "document": attachment,
            "state": self.state(),
        }

    def remove_expense_document(
        self, expense_id: str, document_id: str
    ) -> dict[str, Any]:
        expense_id = str(expense_id or "").strip()
        document_id = str(document_id or "").strip()
        removed = self.attachment_store.remove_attachment(
            expense_id,
            document_id,
            expense_ids=self._known_expense_ids(),
        )
        return {
            "ok": True,
            "expense_id": expense_id,
            "deleted": removed,
            "state": self.state(),
        }

    def expense_document_path(self, expense_id: str, document_id: str) -> Path:
        return self.attachment_store.document_path(
            str(expense_id or "").strip(), str(document_id or "").strip()
        )
