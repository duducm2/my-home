"""Orchestrate preview/commit and prompt generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from expense_store import ExpenseStore

from .archive import archive_pack
from .fix import build_fix_text
from .markers import materialize_csv
from .pack_types import get_pack_type
from .validate import parse_csv_rows, validate_price_rows


ROOT = Path(__file__).resolve().parent.parent.parent
PROMPTS_DIR = ROOT / "prompts"


def build_price_discovery_prompt(
    store: ExpenseStore,
    ids: list[str] | None = None,
) -> dict[str, Any]:
    expenses = store.list_expenses()
    if ids:
        idset = set(ids)
        expenses = [item for item in expenses if item["id"] in idset]
        missing_ids = idset - {item["id"] for item in expenses}
        if missing_ids:
            raise ValueError(
                "expense not found: " + ", ".join(sorted(missing_ids))
            )
    # Prefer cost items with room for more quotations when no IDs are given.
    if not ids:
        expenses = [
            item for item in expenses if len(item.get("quotations") or []) < 5
        ]

    template_path = PROMPTS_DIR / "price-discovery.txt"
    template = template_path.read_text(encoding="utf-8") if template_path.is_file() else ""

    context_lines = [
        "id,record_type,category,description,quantity,unit,current_value,quotation_count",
    ]
    for item in expenses:
        qty = "" if item.get("quantity") is None else item["quantity"]
        context_lines.append(
            ",".join(
                [
                    item["id"],
                    item["record_type"],
                    _csv_escape(item["category"]),
                    _csv_escape(item["description"]),
                    str(qty),
                    _csv_escape(item.get("unit") or ""),
                    str(item["value"]),
                    str(len(item.get("quotations") or [])),
                ]
            )
        )

    context_csv = "\n".join(context_lines)
    prompt = template.replace("{{CONTEXT_CSV}}", context_csv)
    prompt = prompt.replace("{{ITEM_COUNT}}", str(len(expenses)))
    return {
        "ok": True,
        "prompt": prompt,
        "filename": "price-discovery-prompt.txt",
        "item_count": len(expenses),
        "ids": [item["id"] for item in expenses],
    }


def _csv_escape(value: str) -> str:
    if any(c in value for c in ',\"\n'):
        return '"' + value.replace('"', '""') + '"'
    return value


def preview_pack(
    pack_text: str,
    pack_id: str = "price",
    *,
    correction_instructions: str = "",
    expense_context: str = "",
) -> dict[str, Any]:
    pack = get_pack_type(pack_id)
    materialized = materialize_csv(pack_text, pack["file_name"])
    if not materialized.get("ok"):
        fix = build_fix_text(
            pack_name=pack["canonical_pack"],
            file_name=pack["file_name"],
            primary_error=materialized.get("error") or "materialize failed",
            headers=pack["headers"],
            rejected_text=pack_text,
            user_instructions=correction_instructions,
            expense_context=expense_context,
        )
        return {
            "ok": False,
            "error": materialized.get("error"),
            "fix_text": fix,
            "filename": pack["fix_filename"],
        }

    headers, raw_rows = parse_csv_rows(materialized["csv_text"])
    if not raw_rows:
        fix = build_fix_text(
            pack_name=pack["canonical_pack"],
            file_name=pack["file_name"],
            primary_error="no data rows in CSV",
            headers=pack["headers"],
            rejected_text=pack_text,
            user_instructions=correction_instructions,
            expense_context=expense_context,
        )
        return {
            "ok": False,
            "error": "no data rows in CSV",
            "fix_text": fix,
            "filename": pack["fix_filename"],
        }

    validated = validate_price_rows(headers, raw_rows, pack["headers"])
    if not validated["ok"]:
        fix = build_fix_text(
            pack_name=pack["canonical_pack"],
            file_name=pack["file_name"],
            primary_error=validated["errors"][0] if validated["errors"] else "validation failed",
            extra_notes=validated["errors"][1:],
            headers=pack["headers"],
            rejected_text=pack_text,
            user_instructions=correction_instructions,
            expense_context=expense_context,
        )
        return {
            "ok": False,
            "error": "validation failed",
            "errors": validated["errors"],
            "fix_text": fix,
            "filename": pack["fix_filename"],
        }

    return {
        "ok": True,
        "rows": validated["rows"],
        "row_count": validated["row_count"],
        "preview": materialized.get("preview") or "",
        "pack_text": pack_text,
    }


def commit_rows(
    store: ExpenseStore,
    rows: list[dict[str, Any]],
    pack_text: str = "",
    pack_id: str = "price",
) -> dict[str, Any]:
    pack = get_pack_type(pack_id)
    result = store.apply_price_rows(rows)
    archived = ""
    if result["ok"] and pack_text.strip():
        archived = archive_pack(store.data_dir, pack_text, prefix=pack["canonical_pack"].replace(".txt", ""))
    return {
        "ok": result["ok"],
        "updated": result["updated"],
        "errors": result.get("errors") or [],
        "archived": archived,
        "state": result["state"],
    }
