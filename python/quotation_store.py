"""Atomic normalized persistence for unit quotations."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from persistence import atomic_write, atomic_write_text


MAX_PDF_BYTES = 25 * 1024 * 1024


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class QuotationStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = data_dir.resolve() / "quotations.json"
        self.documents_dir = self.data_dir / "private" / "quotations"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write([])

    def _read_document(self) -> dict[str, Any]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"quotations.json is invalid: {exc}") from exc
        if not isinstance(document, dict) or not isinstance(
            document.get("quotations"), list
        ):
            raise ValueError("quotations.json must contain a quotations array")
        return document

    def _write(self, quotations: list[dict[str, Any]]) -> None:
        document = {
            "version": 2,
            "quotations": quotations,
            "updated_at": _stamp(),
        }
        atomic_write_text(
            self.path,
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            backup=self.path.is_file(),
        )

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                dict(item)
                for item in self._read_document()["quotations"]
                if isinstance(item, dict)
            ]

    def for_expense(self, expense_id: str) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in item.items() if key != "expense_id"}
            for item in self.all()
            if str(item.get("expense_id") or "") == expense_id
            and not item.get("archived")
        ]

    def replace_for_expense(
        self, expense_id: str, quotations: list[dict[str, Any]]
    ) -> None:
        self.replace_many({expense_id: quotations})

    def replace_many(self, replacements: dict[str, list[dict[str, Any]]]) -> None:
        with self._lock:
            current = [
                item
                for item in self.all()
                if str(item.get("expense_id") or "") not in replacements
            ]
            for expense_id, quotations in replacements.items():
                current.extend(
                    {"expense_id": expense_id, **dict(item)} for item in quotations
                )
            self._write(current)

    def delete_expense(self, expense_id: str) -> None:
        with self._lock:
            current = self.all()
            stamp = _stamp()
            for item in current:
                if str(item.get("expense_id") or "") == expense_id:
                    item["archived"] = True
                    item["archived_at"] = stamp
            self._write(current)

    def archive(self, expense_id: str, quotation_id: str) -> None:
        with self._lock:
            current = self.all()
            for item in current:
                if (
                    str(item.get("expense_id") or "") == expense_id
                    and str(item.get("id") or "") == quotation_id
                ):
                    item["archived"] = True
                    item["archived_at"] = _stamp()
                    self._write(current)
                    return
            raise ValueError(f"quotation not found: {quotation_id}")

    def add_document(
        self,
        expense_id: str,
        quotation_id: str,
        data: bytes,
        original_filename: str,
    ) -> dict[str, Any]:
        if not data or len(data) > MAX_PDF_BYTES:
            raise ValueError("PDF must contain data and be at most 25 MB")
        if not data.startswith(b"%PDF"):
            raise ValueError("document must be a PDF")
        safe_expense = re.sub(r"[^A-Za-z0-9_-]", "_", expense_id)
        safe_quote = re.sub(r"[^A-Za-z0-9_-]", "_", quotation_id)
        with self._lock:
            items = self.all()
            quotation = next(
                (
                    item
                    for item in items
                    if str(item.get("expense_id") or "") == expense_id
                    and str(item.get("id") or "") == quotation_id
                    and not item.get("archived")
                ),
                None,
            )
            if quotation is None:
                raise ValueError(f"quotation not found: {quotation_id}")
            attachments = list(quotation.get("attachments") or [])
            document_id = f"DOC_{len(attachments) + 1:03d}"
            folder = (self.documents_dir / safe_expense / safe_quote).resolve()
            folder.mkdir(parents=True, exist_ok=True)
            if self.documents_dir not in folder.parents:
                raise ValueError("invalid quotation document path")
            target = folder / f"{document_id.lower()}.pdf"
            atomic_write(target, data, backup=False)
            attachment = {
                "id": document_id,
                "original_filename": Path(original_filename or "quotation.pdf").name,
                "repository_path": target.relative_to(self.data_dir.parent).as_posix(),
                "mime_type": "application/pdf",
                "size_bytes": len(data),
                "pages": len(re.findall(rb"/Type\s*/Page\b", data)) or None,
                "sha256": hashlib.sha256(data).hexdigest(),
                "uploaded_at": _stamp(),
            }
            attachments.append(attachment)
            quotation["attachments"] = attachments
            quotation["updated_at"] = _stamp()
            self._write(items)
            return attachment

    def document_path(
        self, expense_id: str, quotation_id: str, document_id: str = ""
    ) -> Path:
        quotation = next(
            (
                item
                for item in self.all()
                if str(item.get("expense_id") or "") == expense_id
                and str(item.get("id") or "") == quotation_id
            ),
            None,
        )
        if quotation is None:
            raise ValueError(f"quotation not found: {quotation_id}")
        attachments = list(quotation.get("attachments") or [])
        selected = document_id or (
            str(attachments[-1].get("id") or "") if attachments else ""
        )
        attachment = next(
            (item for item in attachments if str(item.get("id") or "") == selected),
            None,
        )
        if attachment is None:
            raise ValueError("quotation document not found")
        target = (
            self.data_dir.parent / str(attachment.get("repository_path") or "")
        ).resolve()
        if self.documents_dir not in target.parents or not target.is_file():
            raise ValueError("quotation document file not found")
        return target
