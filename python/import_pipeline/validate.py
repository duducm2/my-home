"""Validate materialized CSV rows for a pack type."""

from __future__ import annotations

import csv
import io
import math
from typing import Any
from urllib.parse import urlparse


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
    missing_headers = [h for h in ["unit_price", "vendor"] if h not in headers]
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
        if not math.isfinite(unit_price) or unit_price < 0:
            row_errors.append(
                f"line {index}: unit_price must be finite and nonnegative"
            )
            continue
        vendor = row.get("vendor", "").strip()
        if not vendor:
            row_errors.append(f"line {index}: vendor required ({eid or desc})")
            continue
        product_url = row.get("product_url", "").strip()
        if product_url:
            parsed_url = urlparse(product_url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                row_errors.append(
                    f"line {index}: product_url must be valid HTTP(S)"
                )
                continue

        item: dict[str, Any] = {
            "id": eid,
            "description": desc,
            "quotation_id": row.get("quotation_id", ""),
            "unit_price": unit_price,
            "vendor": vendor,
            "product_url": product_url,
            "price_notes": row.get("price_notes", ""),
            "unit": row.get("unit", ""),
            "checked_at": row.get("checked_at", ""),
        }
        numeric_fields = ("quantity", "shipping_cost", "total_price")
        invalid_number = False
        for field in numeric_fields:
            raw_value = row.get(field, "").strip()
            if raw_value == "":
                continue
            try:
                number = float(raw_value.replace(",", "."))
            except ValueError:
                row_errors.append(
                    f"line {index}: invalid {field} {raw_value!r}"
                )
                invalid_number = True
                break
            if not math.isfinite(number) or number < 0:
                row_errors.append(
                    f"line {index}: {field} must be finite and nonnegative"
                )
                invalid_number = True
                break
            item[field] = number
        if invalid_number:
            continue
        selected = row.get("selected", "").strip().lower()
        if selected not in {"", "0", "1", "false", "true", "no", "yes"}:
            row_errors.append(f"line {index}: invalid selected value {selected!r}")
            continue
        item["selected"] = selected in {"1", "true", "yes"}
        parsed.append(item)

    errors.extend(row_errors)
    return {
        "ok": not errors,
        "rows": parsed,
        "errors": errors,
        "row_count": len(parsed),
    }
