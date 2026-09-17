"""Validate materialized CSV rows for a pack type."""

from __future__ import annotations

import csv
from datetime import date
import io
import math
from typing import Any
from urllib.parse import urlparse


METADATA_TEXT_FIELDS = (
    "brand",
    "model",
    "specifications",
    "package_size",
    "availability",
    "seller_location",
    "source_name",
    "ambiguities",
)


def _valid_iso_date(value: str) -> bool:
    if not value:
        return True
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


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
    missing_headers = [header for header in expected_headers if header not in headers]
    if "id" not in headers and "description" not in headers:
        missing_headers.append("id or description")
    if missing_headers:
        errors.append("missing CSV headers: " + ", ".join(missing_headers))
    unexpected_headers = [header for header in headers if header not in expected_headers]
    if unexpected_headers:
        errors.append(
            "unexpected CSV headers: " + ", ".join(unexpected_headers)
        )

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
        currency = row.get("currency", "").strip().upper() or "BRL"
        if currency != "BRL":
            row_errors.append(f"line {index}: currency must be BRL")
            continue
        checked_at = row.get("checked_at", "").strip()
        valid_until = row.get("quote_valid_until", "").strip()
        if not _valid_iso_date(checked_at):
            row_errors.append(f"line {index}: checked_at must be YYYY-MM-DD")
            continue
        if not _valid_iso_date(valid_until):
            row_errors.append(
                f"line {index}: quote_valid_until must be YYYY-MM-DD"
            )
            continue
        source_type = row.get("source_type", "").strip().lower() or "text"
        if source_type not in {"text", "pdf", "manual"}:
            row_errors.append(
                f"line {index}: source_type must be text, pdf, or manual"
            )
            continue
        source_page_raw = row.get("source_page", "").strip()
        source_page: int | None = None
        if source_page_raw:
            try:
                source_page = int(source_page_raw)
            except ValueError:
                row_errors.append(f"line {index}: source_page must be an integer")
                continue
            if source_page < 1:
                row_errors.append(f"line {index}: source_page must be >= 1")
                continue
        confidence_raw = row.get("extraction_confidence", "").strip()
        confidence: float | None = None
        if confidence_raw:
            try:
                confidence = float(confidence_raw.replace(",", "."))
            except ValueError:
                row_errors.append(
                    f"line {index}: extraction_confidence must be numeric"
                )
                continue
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                row_errors.append(
                    f"line {index}: extraction_confidence must be between 0 and 1"
                )
                continue
        quantity = item.get("quantity")
        shipping = item.get("shipping_cost", 0.0)
        total = item.get("total_price")
        if quantity is not None and total is not None:
            calculated = round(unit_price * quantity + shipping, 2)
            if abs(total - calculated) > 0.01:
                row_errors.append(
                    f"line {index}: total_price must equal unit_price * quantity + shipping_cost ({calculated:.2f})"
                )
                continue
        item["currency"] = currency
        item["checked_at"] = checked_at
        item["metadata"] = {
            **{field: row.get(field, "").strip() for field in METADATA_TEXT_FIELDS},
            "quote_valid_until": valid_until,
            "source_type": source_type,
            "source_page": source_page,
            "extraction_confidence": confidence,
        }
        parsed.append(item)

    errors.extend(row_errors)
    return {
        "ok": not errors,
        "rows": parsed,
        "errors": errors,
        "row_count": len(parsed),
    }
