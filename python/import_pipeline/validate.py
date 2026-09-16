"""Validate materialized CSV rows for a pack type."""

from __future__ import annotations

import csv
import io
from typing import Any


def parse_csv_rows(csv_text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    headers = list(reader.fieldnames or [])
    rows: list[dict[str, str]] = []
    for raw in reader:
        if not raw:
            continue
        row = {k: (raw.get(k) or "").strip() for k in headers}
        if any(row.values()):
            rows.append(row)
    return headers, rows


def validate_price_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    expected_headers: list[str],
) -> dict[str, Any]:
    errors: list[str] = []
    missing_headers = [h for h in ["unit_price"] if h not in headers]
    if "id" not in headers and "description" not in headers:
        missing_headers.append("id or description")
    if missing_headers:
        errors.append("missing CSV headers: " + ", ".join(missing_headers))

    parsed: list[dict[str, Any]] = []
    row_errors: list[str] = []
    for index, row in enumerate(rows, start=2):
        eid = row.get("id", "").strip()
        desc = row.get("description", "").strip()
        if not eid and not desc:
            row_errors.append(f"line {index}: need id or description")
            continue
        unit_price_raw = row.get("unit_price", "").strip()
        if unit_price_raw == "":
            row_errors.append(f"line {index}: unit_price required ({eid or desc})")
            continue
        try:
            unit_price = float(unit_price_raw.replace(",", "."))
        except ValueError:
            row_errors.append(f"line {index}: invalid unit_price {unit_price_raw!r}")
            continue

        item: dict[str, Any] = {
            "id": eid,
            "description": desc,
            "unit_price": unit_price,
            "vendor": row.get("vendor", ""),
            "product_url": row.get("product_url", ""),
            "price_notes": row.get("price_notes", ""),
            "unit": row.get("unit", ""),
        }
        qty = row.get("quantity", "").strip()
        if qty != "":
            try:
                item["quantity"] = float(qty.replace(",", "."))
            except ValueError:
                row_errors.append(f"line {index}: invalid quantity {qty!r}")
                continue
        value = row.get("value", "").strip()
        if value != "":
            try:
                item["value"] = float(value.replace(",", "."))
            except ValueError:
                row_errors.append(f"line {index}: invalid value {value!r}")
                continue
        parsed.append(item)

    errors.extend(row_errors)
    return {
        "ok": not errors,
        "rows": parsed,
        "errors": errors,
        "row_count": len(parsed),
    }
