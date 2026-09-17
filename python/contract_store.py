"""Validated contract metadata and versioned PDF persistence."""

from __future__ import annotations

import csv
import calendar
import hashlib
import json
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from persistence import atomic_write, atomic_write_text, coordinated_write

CONTRACT_TYPES = {"purchase", "service"}
CONTRACT_STATUSES = {"draft", "signed", "active", "completed", "cancelled"}
PAYMENT_FREQUENCIES = {"one_time", "weekly", "monthly", "custom"}
MAX_PDF_BYTES = 25 * 1024 * 1024


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _date(value: Any, field: str, required: bool = False) -> str:
    text = str(value or "").strip()
    if not text and not required:
        return ""
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must use YYYY-MM-DD") from exc
    return text


class ContractStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "contracts.json"
        self.providers_path = self.data_dir / "providers.json"
        self.expenses_path = self.data_dir / "expenses.csv"
        self.documents_dir = self.data_dir / "private" / "contracts"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({"version": 2, "contracts": [], "updated_at": now_stamp()})
        self._ensure_payment_plans()

    def _read(self) -> dict[str, Any]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"contracts.json is invalid: {exc}") from exc
            if not isinstance(payload.get("contracts"), list):
                raise ValueError("contracts.json must contain a contracts array")
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

    def _linked_task_period(
        self, expense_ids: list[str], contract_title: str = ""
    ) -> tuple[str, str]:
        path = self.data_dir / "tasks.json"
        if not path.is_file() or not expense_ids:
            return "", ""
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return "", ""
        selected = set(expense_ids)
        tasks = [
            item
            for item in document.get("tasks", [])
            if isinstance(item, dict)
            and (
                str(item.get("expense_id") or "") in selected
                or any(
                    isinstance(allocation, dict)
                    and str(allocation.get("expense_id") or "") in selected
                    for allocation in item.get("expense_allocations") or []
                )
            )
        ]
        if not tasks and contract_title:
            contract_words = {
                word
                for word in re.findall(r"\w+", contract_title.casefold())
                if len(word) > 3
            }
            ranked = sorted(
                (
                    (
                        len(
                            contract_words
                            & {
                                word
                                for word in re.findall(
                                    r"\w+", str(item.get("title") or "").casefold()
                                )
                                if len(word) > 3
                            }
                        ),
                        item,
                    )
                    for item in document.get("tasks", [])
                    if isinstance(item, dict)
                    and item.get("activity_type") == "macro"
                ),
                key=lambda pair: pair[0],
                reverse=True,
            )
            if ranked and ranked[0][0] >= 2:
                tasks = [ranked[0][1]]
        starts = [str(item.get("start_date") or "") for item in tasks if item.get("start_date")]
        ends = [str(item.get("end_date") or "") for item in tasks if item.get("end_date")]
        return (min(starts, default=""), max(ends, default=""))

    @staticmethod
    def _add_month(value: date) -> date:
        year = value.year + (1 if value.month == 12 else 0)
        month = 1 if value.month == 12 else value.month + 1
        return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))

    @classmethod
    def _payment_dates(
        cls, start_date: str, end_date: str, frequency: str
    ) -> list[str]:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if frequency == "one_time":
            return [end.isoformat()]
        dates = [start]
        cursor = start
        while True:
            next_date = (
                cursor + timedelta(days=7)
                if frequency == "weekly"
                else cls._add_month(cursor)
            )
            if next_date >= end:
                break
            dates.append(next_date)
            cursor = next_date
        if dates[-1] != end:
            dates.append(end)
        return [value.isoformat() for value in dates]

    @staticmethod
    def _equal_payments(
        amount: float,
        payment_dates: list[str],
        frequency: str,
        date_status: str,
    ) -> list[dict[str, Any]]:
        total_cents = round(amount * 100)
        count = max(1, len(payment_dates))
        base, remainder = divmod(total_cents, count)
        return [
            {
                "id": f"PAY_{index:03d}",
                "date": payment_date,
                "amount": (base + (1 if index <= remainder else 0)) / 100,
                "date_status": date_status,
                "source": f"contract_{frequency}",
                "notes": "",
            }
            for index, payment_date in enumerate(payment_dates, start=1)
        ]

    @staticmethod
    def _validate_custom_payments(
        payload: Any, amount: float, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or not payload or len(payload) > 104:
            raise ValueError("custom payment schedule must contain 1 to 104 items")
        payments = []
        ids: set[str] = set()
        for index, raw in enumerate(payload, start=1):
            if not isinstance(raw, dict):
                raise ValueError("each contract payment must be an object")
            payment_id = str(raw.get("id") or f"PAY_{index:03d}").strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", payment_id) or payment_id in ids:
                raise ValueError(f"invalid or duplicate contract payment id: {payment_id}")
            ids.add(payment_id)
            payment_date = _date(raw.get("date"), "payment date", required=True)
            if payment_date < start_date or payment_date > end_date:
                raise ValueError("contract payments must be inside the work period")
            try:
                payment_amount = round(float(raw.get("amount")), 2)
            except (TypeError, ValueError) as exc:
                raise ValueError("contract payment amount must be numeric") from exc
            if payment_amount < 0:
                raise ValueError("contract payment amount must be non-negative")
            date_status = str(raw.get("date_status") or "confirmed")
            if date_status not in {"estimated", "confirmed"}:
                raise ValueError("invalid contract payment date status")
            payments.append(
                {
                    "id": payment_id,
                    "date": payment_date,
                    "amount": payment_amount,
                    "date_status": date_status,
                    "source": "contract_custom",
                    "notes": str(raw.get("notes") or "").strip()[:500],
                }
            )
        if abs(sum(item["amount"] for item in payments) - amount) > 0.01:
            raise ValueError("contract payment amounts must equal the total price")
        return sorted(payments, key=lambda item: (item["date"], item["id"]))

    def _ensure_payment_plans(self) -> None:
        with self._lock:
            document = self._read()
            changed = int(document.get("version") or 1) < 2
            for index, item in enumerate(document["contracts"]):
                if str(item.get("type") or "service") != "service":
                    continue
                previously_confirmed = (
                    item.get("work_period_status") == "confirmed"
                )
                had_start = bool(item.get("start_date")) and (
                    previously_confirmed or "work_period_status" not in item
                )
                had_end = bool(item.get("end_date")) and (
                    previously_confirmed or "work_period_status" not in item
                )
                task_start, task_end = self._linked_task_period(
                    [str(value) for value in item.get("expense_ids") or []],
                    str(item.get("title") or ""),
                )
                start_date = str(
                    item.get("start_date") if had_start else task_start
                )
                start_date = start_date or str(item.get("start_date") or "")
                if not start_date:
                    start_date = (date.today() + timedelta(days=index * 7)).isoformat()
                end_date = str(item.get("end_date") if had_end else "")
                if not end_date:
                    raw_duration = (
                        ((item.get("metadata") or {}).get("deadline") or {}).get(
                            "duration_days"
                        )
                    )
                    if raw_duration:
                        end_date = (
                            date.fromisoformat(start_date)
                            + timedelta(days=max(0, int(raw_duration) - 1))
                        ).isoformat()
                    else:
                        end_date = task_end or start_date
                frequency = str(item.get("payment_frequency") or "monthly")
                if frequency not in PAYMENT_FREQUENCIES:
                    frequency = "monthly"
                dates_changed = (
                    item.get("start_date") != start_date
                    or item.get("end_date") != end_date
                )
                if not item.get("payment_schedule") or (
                    dates_changed
                    and item.get("work_period_status") == "estimated"
                    and frequency != "custom"
                ):
                    item["payment_schedule"] = self._equal_payments(
                        float(item.get("amount") or 0),
                        self._payment_dates(start_date, end_date, frequency),
                        frequency,
                        "confirmed" if had_start and had_end else "estimated",
                    )
                    changed = True
                if (
                    item.get("start_date") != start_date
                    or item.get("end_date") != end_date
                    or item.get("payment_frequency") != frequency
                ):
                    item["start_date"] = start_date
                    item["end_date"] = end_date
                    item["work_period_status"] = (
                        "confirmed" if had_start and had_end else "estimated"
                    )
                    item["payment_frequency"] = frequency
                    changed = True
            if changed:
                self._write(document)

    def _provider_ids(self) -> set[str]:
        if not self.providers_path.is_file():
            return set()
        payload = json.loads(self.providers_path.read_text(encoding="utf-8-sig"))
        return {str(item.get("id")) for item in payload.get("providers") or []}

    def _expense_ids(self, service_only: bool = False) -> set[str]:
        if not self.expenses_path.is_file():
            return set()
        with self.expenses_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return {
                str(row.get("id"))
                for row in csv.DictReader(handle)
                if not service_only
                or str(row.get("record_type") or ("material" if row.get("category") == "Material" else "service")) == "service"
            }

    def _sync_expense_rows(self, contract_id: str, selected_ids: list[str], provider_id: str) -> None:
        if not self.expenses_path.is_file():
            return
        with self.expenses_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = list(reader.fieldnames or [])
            rows = list(reader)
        if "contract_ids_json" not in headers:
            headers.append("contract_ids_json")
        selected = set(selected_ids)
        changed = False
        for row in rows:
            expense_id = str(row.get("id") or "")
            try:
                contract_ids = json.loads(row.get("contract_ids_json") or "[]")
            except json.JSONDecodeError:
                contract_ids = []
            if not isinstance(contract_ids, list):
                contract_ids = []
            legacy = str(row.get("contract_id") or "")
            contract_ids = list(
                dict.fromkeys(
                    [
                        *(str(value) for value in contract_ids if str(value)),
                        *([legacy] if legacy else []),
                    ]
                )
            )
            if expense_id in selected:
                if contract_id not in contract_ids:
                    contract_ids.append(contract_id)
                if row.get("provider_id") != provider_id:
                    row["provider_id"] = provider_id
            elif contract_id in contract_ids:
                contract_ids = [value for value in contract_ids if value != contract_id]
            serialized = json.dumps(
                contract_ids, ensure_ascii=False, separators=(",", ":")
            )
            primary = contract_ids[0] if contract_ids else ""
            if (
                row.get("contract_ids_json") != serialized
                or row.get("contract_id") != primary
            ):
                row["contract_ids_json"] = serialized
                row["contract_id"] = primary
                if not contract_ids:
                    row["provider_id"] = ""
                row["updated_at"] = now_stamp()
                changed = True
        if changed:
            temporary = self.expenses_path.with_suffix(".csv.render")
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
                writer.writeheader()
                writer.writerows({key: row.get(key, "") for key in headers} for row in rows)
            atomic_write(self.expenses_path, temporary.read_bytes())
            temporary.unlink()

    @staticmethod
    def _next_id(contracts: list[dict[str, Any]]) -> str:
        maximum = 0
        for item in contracts:
            match = re.fullmatch(r"CONTRACT_(\d+)", str(item.get("id") or ""))
            if match:
                maximum = max(maximum, int(match.group(1)))
        return f"CONTRACT_{maximum + 1:04d}"

    @staticmethod
    def _normalize(item: dict[str, Any]) -> dict[str, Any]:
        start_date = str(item.get("start_date") or "")
        end_date = str(item.get("end_date") or "")
        work_days = (
            (date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1
            if start_date and end_date
            else 0
        )
        return {
            "id": str(item.get("id") or ""),
            "type": str(item.get("type") or "service"),
            "title": str(item.get("title") or ""),
            "provider_id": str(item.get("provider_id") or ""),
            "expense_ids": [str(value) for value in item.get("expense_ids") or []],
            "status": str(item.get("status") or "draft"),
            "amount": float(item.get("amount") or 0),
            "start_date": start_date,
            "end_date": end_date,
            "work_days": work_days,
            "work_period_status": str(
                item.get("work_period_status") or "confirmed"
            ),
            "payment_frequency": str(
                item.get("payment_frequency") or "one_time"
            ),
            "payment_schedule": list(item.get("payment_schedule") or []),
            "notes": str(item.get("notes") or ""),
            "archived": bool(item.get("archived")),
            "document_versions": list(item.get("document_versions") or []),
            "current_document_id": str(item.get("current_document_id") or ""),
            "metadata": dict(item.get("metadata") or {}),
            "created_at": str(item.get("created_at") or ""),
            "updated_at": str(item.get("updated_at") or ""),
        }

    def state(self, include_archived: bool = True) -> dict[str, Any]:
        document = self._read()
        contracts = [self._normalize(item) for item in document["contracts"] if include_archived or not item.get("archived")]
        contracts.sort(key=lambda item: (bool(item["archived"]), item["type"] != "purchase", item["start_date"], item["title"].casefold()))
        return {
            "ok": True,
            "contracts": contracts,
            "types": sorted(CONTRACT_TYPES),
            "statuses": sorted(CONTRACT_STATUSES),
            "count": len(contracts),
            "updated_at": document.get("updated_at", ""),
        }

    def upsert(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("contract title is required")
        contract_type = str(payload.get("type") or "service").strip()
        if contract_type not in CONTRACT_TYPES:
            raise ValueError(f"invalid contract type: {contract_type}")
        status = str(payload.get("status") or "draft").strip()
        if status not in CONTRACT_STATUSES:
            raise ValueError(f"invalid contract status: {status}")
        provider_id = str(payload.get("provider_id") or "").strip()
        if provider_id and provider_id not in self._provider_ids():
            raise ValueError(f"provider not found: {provider_id}")
        if contract_type == "service" and not provider_id:
            raise ValueError("service contracts require a provider")
        expense_ids = list(dict.fromkeys(str(value) for value in payload.get("expense_ids") or [] if str(value)))
        invalid_expenses = set(expense_ids) - self._expense_ids(service_only=contract_type == "service")
        if invalid_expenses:
            raise ValueError(f"service expenses not found: {', '.join(sorted(invalid_expenses))}")
        try:
            amount = float(payload.get("amount") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("amount must be numeric") from exc
        if amount < 0:
            raise ValueError("amount must be non-negative")
        start_date = _date(payload.get("start_date"), "start_date")
        end_date = _date(payload.get("end_date"), "end_date")
        work_period_status = str(
            payload.get("work_period_status") or "confirmed"
        ).strip()
        if work_period_status not in {"estimated", "confirmed"}:
            raise ValueError(
                "work_period_status must be estimated or confirmed"
            )
        if contract_type == "service" and (not start_date or not end_date):
            linked_start, linked_end = self._linked_task_period(
                expense_ids, title
            )
            if not start_date and linked_start:
                start_date = linked_start
                work_period_status = "estimated"
            if not end_date and linked_end:
                end_date = linked_end
                work_period_status = "estimated"
        if contract_type == "service" and not start_date:
            raise ValueError("service contracts require a work start date")
        if contract_type == "service" and not end_date:
            end_date = start_date
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        payment_frequency = str(
            payload.get("payment_frequency") or "one_time"
        ).strip()
        if payment_frequency not in PAYMENT_FREQUENCIES:
            raise ValueError(f"invalid payment frequency: {payment_frequency}")
        if contract_type == "service":
            if payment_frequency == "custom":
                payment_schedule = self._validate_custom_payments(
                    payload.get("payment_schedule"),
                    amount,
                    start_date,
                    end_date,
                )
            else:
                payment_schedule = self._equal_payments(
                    amount,
                    self._payment_dates(
                        start_date, end_date, payment_frequency
                    ),
                    payment_frequency,
                    work_period_status,
                )
        else:
            payment_frequency = "one_time"
            payment_schedule = []

        with self._lock:
            document = self._read()
            contracts = list(document["contracts"])
            contract_id = str(payload.get("id") or "").strip()
            existing: dict[str, Any] | None = None
            index = -1
            if contract_id:
                for index, item in enumerate(contracts):
                    if str(item.get("id")) == contract_id:
                        existing = item
                        break
                else:
                    raise ValueError(f"contract not found: {contract_id}")
            else:
                contract_id = self._next_id(contracts)
            stamp = now_stamp()
            item = {
                "id": contract_id,
                "type": contract_type,
                "title": title,
                "provider_id": provider_id,
                "expense_ids": expense_ids,
                "status": status,
                "amount": amount,
                "start_date": start_date,
                "end_date": end_date,
                "work_period_status": work_period_status,
                "payment_frequency": payment_frequency,
                "payment_schedule": payment_schedule,
                "notes": str(payload.get("notes") or "").strip(),
                "archived": bool((existing or {}).get("archived", False)),
                "document_versions": list((existing or {}).get("document_versions") or []),
                "current_document_id": str((existing or {}).get("current_document_id") or ""),
                "metadata": dict((existing or {}).get("metadata") or payload.get("metadata") or {}),
                "created_at": str((existing or {}).get("created_at") or stamp),
                "updated_at": stamp,
            }
            if existing is None:
                contracts.append(item)
            else:
                contracts[index] = item
            document["contracts"] = contracts
            with coordinated_write([self.path, self.expenses_path]):
                self._write(document)
                self._sync_expense_rows(contract_id, expense_ids, provider_id)
            return {"ok": True, "contract_id": contract_id, **self.state()}

    def archive(self, contract_id: str) -> dict[str, Any]:
        with self._lock:
            document = self._read()
            for item in document["contracts"]:
                if str(item.get("id")) == contract_id:
                    item["archived"] = True
                    item["updated_at"] = now_stamp()
                    break
            else:
                raise ValueError(f"contract not found: {contract_id}")
            self._write(document)
            return {"ok": True, "archived": contract_id, **self.state()}

    def sync_expense_link(
        self, expense_id: str, contract_ids: list[str] | str | None = None
    ) -> None:
        requested = (
            {str(value) for value in contract_ids if str(value)}
            if isinstance(contract_ids, list)
            else ({str(contract_ids)} if contract_ids else set())
        )
        with self._lock:
            document = self._read()
            changed = False
            for contract in document["contracts"]:
                linked = list(contract.get("expense_ids") or [])
                should_link = str(contract.get("id")) in requested
                if expense_id in linked and not should_link:
                    contract["expense_ids"] = [value for value in linked if value != expense_id]
                    contract["updated_at"] = now_stamp()
                    changed = True
                elif should_link and expense_id not in linked:
                    contract["expense_ids"] = [*linked, expense_id]
                    contract["updated_at"] = now_stamp()
                    changed = True
            known = {str(item.get("id")) for item in document["contracts"]}
            missing = requested - known
            if missing:
                raise ValueError(f"contract not found: {', '.join(sorted(missing))}")
            if changed:
                self._write(document)

    def add_document(self, contract_id: str, data: bytes, original_filename: str) -> dict[str, Any]:
        if len(data) > MAX_PDF_BYTES:
            raise ValueError("PDF exceeds the 25 MB limit")
        if not data.startswith(b"%PDF"):
            raise ValueError("document must be a PDF")
        with self._lock:
            document = self._read()
            contract = next((item for item in document["contracts"] if str(item.get("id")) == contract_id), None)
            if contract is None:
                raise ValueError(f"contract not found: {contract_id}")
            versions = list(contract.get("document_versions") or [])
            document_id = f"DOC_{len(versions) + 1:03d}"
            folder = (self.documents_dir / re.sub(r"[^A-Za-z0-9_-]", "_", contract_id)).resolve()
            folder.mkdir(parents=True, exist_ok=True)
            if self.documents_dir not in folder.parents:
                raise ValueError("invalid contract document path")
            filename = f"{document_id.lower()}.pdf"
            target = folder / filename
            atomic_write(target, data, backup=False)
            version = {
                "id": document_id,
                "original_filename": Path(original_filename or "contract.pdf").name,
                "repository_path": target.relative_to(self.data_dir.parent).as_posix(),
                "mime_type": "application/pdf",
                "size_bytes": len(data),
                "pages": len(re.findall(rb"/Type\s*/Page\b", data)) or None,
                "sha256": hashlib.sha256(data).hexdigest(),
                "uploaded_at": now_stamp(),
            }
            versions.append(version)
            contract["document_versions"] = versions
            contract["current_document_id"] = document_id
            contract["updated_at"] = now_stamp()
            self._write(document)
            return {"ok": True, "contract_id": contract_id, "document": version, **self.state()}

    def document_path(self, contract_id: str, document_id: str = "") -> Path:
        contract = next((item for item in self._read()["contracts"] if str(item.get("id")) == contract_id), None)
        if contract is None:
            raise ValueError(f"contract not found: {contract_id}")
        selected_id = document_id or str(contract.get("current_document_id") or "")
        version = next((item for item in contract.get("document_versions") or [] if str(item.get("id")) == selected_id), None)
        if version is None:
            raise ValueError("contract document not found")
        target = (self.data_dir.parent / str(version["repository_path"])).resolve()
        if self.documents_dir not in target.parents or not target.is_file():
            raise ValueError("contract document file not found")
        return target
