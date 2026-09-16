"""Validated contract metadata and versioned PDF persistence."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any


CONTRACT_TYPES = {"purchase", "service"}
CONTRACT_STATUSES = {"draft", "signed", "active", "completed", "cancelled"}
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
            self._write({"version": 1, "contracts": [], "updated_at": now_stamp()})

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
            document["version"] = 1
            document["updated_at"] = now_stamp()
            temporary = self.path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            os.replace(temporary, self.path)

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
        selected = set(selected_ids)
        changed = False
        for row in rows:
            expense_id = str(row.get("id") or "")
            if expense_id in selected:
                if row.get("contract_id") != contract_id or row.get("provider_id") != provider_id:
                    row["contract_id"] = contract_id
                    row["provider_id"] = provider_id
                    row["updated_at"] = now_stamp()
                    changed = True
            elif row.get("contract_id") == contract_id:
                row["contract_id"] = ""
                row["provider_id"] = ""
                row["updated_at"] = now_stamp()
                changed = True
        if changed:
            with self.expenses_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
                writer.writeheader()
                writer.writerows({key: row.get(key, "") for key in headers} for row in rows)

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
        return {
            "id": str(item.get("id") or ""),
            "type": str(item.get("type") or "service"),
            "title": str(item.get("title") or ""),
            "provider_id": str(item.get("provider_id") or ""),
            "expense_ids": [str(value) for value in item.get("expense_ids") or []],
            "status": str(item.get("status") or "draft"),
            "amount": float(item.get("amount") or 0),
            "start_date": str(item.get("start_date") or ""),
            "end_date": str(item.get("end_date") or ""),
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
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

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

    def sync_expense_link(self, expense_id: str, contract_id: str = "") -> None:
        with self._lock:
            document = self._read()
            changed = False
            for contract in document["contracts"]:
                linked = list(contract.get("expense_ids") or [])
                should_link = str(contract.get("id")) == contract_id
                if expense_id in linked and not should_link:
                    contract["expense_ids"] = [value for value in linked if value != expense_id]
                    contract["updated_at"] = now_stamp()
                    changed = True
                elif should_link and expense_id not in linked:
                    contract["expense_ids"] = [*linked, expense_id]
                    contract["updated_at"] = now_stamp()
                    changed = True
            if contract_id and not any(str(item.get("id")) == contract_id for item in document["contracts"]):
                raise ValueError(f"contract not found: {contract_id}")
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
            temporary = target.with_suffix(".pdf.tmp")
            temporary.write_bytes(data)
            os.replace(temporary, target)
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
