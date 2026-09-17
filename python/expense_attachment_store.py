"""Expense-level PDF attachments (uploads + links to system documents)."""

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


SYSTEM_DOCUMENT_ALIASES = {
    "purchase-contract": "purchase-contract-2026-09-08",
    "gelson-contract-01": "gelson-contract-01-draft",
    "gelson-contract-02": "gelson-contract-02-draft",
}


def list_system_documents(data_dir: Path) -> list[dict[str, Any]]:
    documents_dir = data_dir.resolve() / "documents"
    if not documents_dir.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(documents_dir.glob("*.pdf")):
        document_id = path.stem
        items.append(
            {
                "id": document_id,
                "filename": path.name,
                "label": document_id.replace("-", " ").replace("_", " "),
                "size_bytes": path.stat().st_size,
                "url": f"/api/project/documents/{document_id}",
            }
        )
    return items


def system_document_path(data_dir: Path, document_id: str) -> Path:
    safe_id = str(document_id or "").strip()
    if safe_id.endswith(".pdf"):
        safe_id = safe_id[: -len(".pdf")]
    safe_id = SYSTEM_DOCUMENT_ALIASES.get(safe_id, safe_id)
    if not safe_id or "/" in safe_id or "\\" in safe_id or ".." in safe_id:
        raise ValueError("invalid system document id")
    documents_dir = (data_dir.resolve() / "documents").resolve()
    target = (documents_dir / f"{safe_id}.pdf").resolve()
    if target.parent != documents_dir or not target.is_file():
        raise ValueError("system document not found")
    return target


class ExpenseAttachmentStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.path = self.data_dir / "expense-attachments.json"
        self.documents_dir = self.data_dir / "private" / "expenses"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.is_file():
            self._write({})

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"expense-attachments.json is invalid: {exc}") from exc
        if not isinstance(document, dict):
            raise ValueError("expense-attachments.json must be an object")
        by_expense = document.get("by_expense")
        if by_expense is None and "version" not in document:
            # tolerate plain map of expense_id -> attachments
            by_expense = document
        if not isinstance(by_expense, dict):
            raise ValueError("expense-attachments.json must contain by_expense")
        result: dict[str, list[dict[str, Any]]] = {}
        for expense_id, attachments in by_expense.items():
            if isinstance(attachments, list):
                result[str(expense_id)] = [
                    item for item in attachments if isinstance(item, dict)
                ]
        return result

    def _write(self, by_expense: dict[str, list[dict[str, Any]]]) -> None:
        atomic_write_text(
            self.path,
            json.dumps(
                {
                    "version": 1,
                    "updated_at": _stamp(),
                    "by_expense": by_expense,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )

    def for_expense(self, expense_id: str) -> list[dict[str, Any]]:
        return list(self._read().get(str(expense_id), []))

    def _next_id(self, attachments: list[dict[str, Any]]) -> str:
        maximum = 0
        for item in attachments:
            match = re.fullmatch(r"DOC_(\d+)", str(item.get("id") or ""))
            if match:
                maximum = max(maximum, int(match.group(1)))
        return f"DOC_{maximum + 1:03d}"

    def _require_expense(self, expense_ids: set[str], expense_id: str) -> None:
        if expense_id not in expense_ids:
            raise ValueError(f"expense not found: {expense_id}")

    def add_upload(
        self,
        expense_id: str,
        data: bytes,
        original_filename: str,
        *,
        expense_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        if expense_ids is not None:
            self._require_expense(expense_ids, expense_id)
        if not data or len(data) > MAX_PDF_BYTES:
            raise ValueError("PDF must contain data and be at most 25 MB")
        if not data.startswith(b"%PDF"):
            raise ValueError("document must be a PDF")
        safe_expense = re.sub(r"[^A-Za-z0-9_-]", "_", expense_id)
        with self._lock:
            by_expense = self._read()
            attachments = list(by_expense.get(expense_id, []))
            document_id = self._next_id(attachments)
            folder = (self.documents_dir / safe_expense).resolve()
            folder.mkdir(parents=True, exist_ok=True)
            if self.documents_dir not in folder.parents:
                raise ValueError("invalid expense document path")
            target = folder / f"{document_id.lower()}.pdf"
            atomic_write(target, data, backup=False)
            attachment = {
                "id": document_id,
                "source": "upload",
                "original_filename": Path(original_filename or "expense.pdf").name,
                "repository_path": target.relative_to(self.data_dir.parent).as_posix(),
                "mime_type": "application/pdf",
                "size_bytes": len(data),
                "pages": len(re.findall(rb"/Type\s*/Page\b", data)) or None,
                "sha256": hashlib.sha256(data).hexdigest(),
                "uploaded_at": _stamp(),
            }
            attachments.append(attachment)
            by_expense[expense_id] = attachments
            self._write(by_expense)
            return attachment

    def attach_system_document(
        self,
        expense_id: str,
        system_document_id: str,
        *,
        expense_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        if expense_ids is not None:
            self._require_expense(expense_ids, expense_id)
        path = system_document_path(self.data_dir, system_document_id)
        with self._lock:
            by_expense = self._read()
            attachments = list(by_expense.get(expense_id, []))
            for item in attachments:
                if (
                    item.get("source") == "system"
                    and str(item.get("system_document_id") or "") == path.stem
                ):
                    return item
            document_id = self._next_id(attachments)
            attachment = {
                "id": document_id,
                "source": "system",
                "system_document_id": path.stem,
                "original_filename": path.name,
                "mime_type": "application/pdf",
                "size_bytes": path.stat().st_size,
                "uploaded_at": _stamp(),
            }
            attachments.append(attachment)
            by_expense[expense_id] = attachments
            self._write(by_expense)
            return attachment

    def remove_attachment(
        self,
        expense_id: str,
        document_id: str,
        *,
        expense_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        if expense_ids is not None:
            self._require_expense(expense_ids, expense_id)
        with self._lock:
            by_expense = self._read()
            attachments = list(by_expense.get(expense_id, []))
            selected = next(
                (
                    item
                    for item in attachments
                    if str(item.get("id") or "") == document_id
                ),
                None,
            )
            if selected is None:
                raise ValueError("expense document not found")
            remaining = [
                item for item in attachments if str(item.get("id") or "") != document_id
            ]
            if remaining:
                by_expense[expense_id] = remaining
            else:
                by_expense.pop(expense_id, None)
            self._write(by_expense)
            if selected.get("source") == "upload":
                target = (
                    self.data_dir.parent / str(selected.get("repository_path") or "")
                ).resolve()
                if self.documents_dir in target.parents and target.is_file():
                    target.unlink()
            return selected

    def document_path(self, expense_id: str, document_id: str) -> Path:
        attachments = self.for_expense(expense_id)
        attachment = next(
            (item for item in attachments if str(item.get("id") or "") == document_id),
            None,
        )
        if attachment is None:
            raise ValueError("expense document not found")
        if attachment.get("source") == "system":
            return system_document_path(
                self.data_dir, str(attachment.get("system_document_id") or "")
            )
        target = (
            self.data_dir.parent / str(attachment.get("repository_path") or "")
        ).resolve()
        if self.documents_dir not in target.parents or not target.is_file():
            raise ValueError("expense document file not found")
        return target

    def delete_expense(self, expense_id: str) -> None:
        with self._lock:
            by_expense = self._read()
            attachments = list(by_expense.pop(expense_id, []))
            self._write(by_expense)
        safe_expense = re.sub(r"[^A-Za-z0-9_-]", "_", expense_id)
        folder = (self.documents_dir / safe_expense).resolve()
        if self.documents_dir in folder.parents and folder.is_dir():
            for path in folder.glob("*.pdf"):
                path.unlink(missing_ok=True)
            try:
                folder.rmdir()
            except OSError:
                pass
        for item in attachments:
            if item.get("source") != "upload":
                continue
            try:
                target = (
                    self.data_dir.parent / str(item.get("repository_path") or "")
                ).resolve()
            except Exception:
                continue
            if self.documents_dir in target.parents and target.is_file():
                target.unlink(missing_ok=True)
