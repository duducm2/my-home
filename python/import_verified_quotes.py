"""Validate researched offers and import canonical quotation packs.

Research files are intentionally kept separate from application persistence so
their evidence can be reviewed before this script is run with ``--commit``.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESEARCH_DIR = DATA_DIR / "research"
sys.path.insert(0, str(ROOT / "python"))

from expense_store import ExpenseStore  # noqa: E402
from import_pipeline.pack_types import PRICE_PACK  # noqa: E402
from import_pipeline.pipeline import commit_rows, preview_pack  # noqa: E402


EXCLUDED_EXPENSE_IDS = {
    "EXP_0005",  # Mudança ligada ao imóvel anterior.
    "EXP_0009",  # Multa do aluguel anterior.
    "EXP_0010",  # Reforma do apartamento anterior.
    "EXP_0012",  # Aluguel do imóvel anterior.
    "EXP_0018",  # Ferramentas ordinárias são responsabilidade do contratado.
    "EXP_0020",  # Carrinho de mão é ferramenta ordinária do contratado.
}


def _number(value: Any, field: str, expense_id: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{expense_id}: invalid {field}: {value!r}") from exc
    if number < 0:
        raise ValueError(f"{expense_id}: {field} cannot be negative")
    return round(number, 4)


def _research_documents() -> list[tuple[Path, dict[str, Any]]]:
    documents = []
    for path in sorted(RESEARCH_DIR.glob("quotes-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name}: root must be an object")
        documents.append((path, payload))
    if not documents:
        raise ValueError(f"no quote research files found in {RESEARCH_DIR}")
    return documents


def _text(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _canonical_offer(offer: dict[str, Any]) -> dict[str, Any]:
    price_data = offer.get("price_brl")
    price_data = price_data if isinstance(price_data, dict) else {}
    normalized_price = offer.get("normalized_unit_price")
    if normalized_price in {None, ""}:
        normalized_price = offer.get("normalized_price_brl")
    if normalized_price in {None, ""}:
        normalized_price = price_data.get("amount")
    if normalized_price in {None, ""}:
        normalized_price = price_data.get("min")
    displayed_price = offer.get("displayed_price")
    if displayed_price in {None, ""}:
        displayed_price = price_data.get("amount", normalized_price)
    evidence = _text(offer.get("evidence"))
    if not evidence:
        evidence = " — ".join(
            value
            for value in (
                _text(offer.get("offer_name")),
                _text(offer.get("specs_package")),
            )
            if value
        )
    ambiguities = "; ".join(
        value
        for value in (
            _text(offer.get("ambiguities")),
            _text(offer.get("location_caveat")),
        )
        if value
    )
    return {
        **offer,
        "url": _text(offer.get("url") or offer.get("direct_url")),
        "normalized_unit_price": normalized_price,
        "displayed_price": displayed_price,
        "shipping_cost": offer.get("shipping_cost", offer.get("shipping_brl")),
        "evidence": evidence,
        "ambiguities": ambiguities,
        "specifications": _text(
            offer.get("specifications") or offer.get("specs_package")
        ),
        "seller_location": _text(
            offer.get("seller_location") or offer.get("location_caveat")
        ),
    }


def _offers_by_expense() -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []
    for path, document in _research_documents():
        expenses = document.get("expenses")
        if not isinstance(expenses, list):
            raise ValueError(f"{path.name}: expenses must be a list")
        for item in expenses:
            if not isinstance(item, dict):
                raise ValueError(f"{path.name}: expense entry must be an object")
            expense_id = str(item.get("expense_id") or "").strip()
            if not expense_id:
                raise ValueError(f"{path.name}: expense_id is required")
            if expense_id in EXCLUDED_EXPENSE_IDS:
                warnings.append(f"{expense_id}: ignored because it is out of scope")
                continue
            offers = item.get("offers")
            if not isinstance(offers, list):
                raise ValueError(f"{expense_id}: offers must be a list")
            for offer in offers:
                if not isinstance(offer, dict):
                    raise ValueError(f"{expense_id}: offer must be an object")
                if offer.get("eligible_for_import") is False:
                    continue
                offer = _canonical_offer(offer)
                offer["_research_file"] = path.name
                offer["_comparable_spec"] = str(
                    item.get("comparable_spec") or ""
                ).strip()
                grouped.setdefault(expense_id, []).append(offer)
            unresolved = str(item.get("unresolved_notes") or "").strip()
            if unresolved:
                warnings.append(f"{expense_id}: {unresolved}")
    for expense_id, offers in list(grouped.items()):
        vendors = {
            str(offer.get("vendor") or "").strip().casefold()
            for offer in offers
            if str(offer.get("vendor") or "").strip()
        }
        if len(offers) < 3 or len(vendors) < 3:
            warnings.append(
                f"{expense_id}: not imported because fewer than 3 distinct "
                "eligible offers were verified"
            )
            del grouped[expense_id]
    return grouped, warnings


def _validate_offers(
    expenses: dict[str, dict[str, Any]],
    offers_by_expense: dict[str, list[dict[str, Any]]],
) -> list[str]:
    errors: list[str] = []
    for expense_id, offers in sorted(offers_by_expense.items()):
        expense = expenses.get(expense_id)
        if expense is None:
            errors.append(f"{expense_id}: expense does not exist")
            continue
        if len(offers) < 3:
            errors.append(f"{expense_id}: only {len(offers)} offers; need at least 3")
        vendors: set[str] = set()
        urls: set[str] = set()
        for index, offer in enumerate(offers, start=1):
            vendor = str(offer.get("vendor") or "").strip()
            url = str(offer.get("url") or "").strip()
            if not vendor:
                errors.append(f"{expense_id} offer {index}: vendor is required")
            vendors.add(vendor.casefold())
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{expense_id} offer {index}: invalid direct URL")
            if url in urls:
                errors.append(f"{expense_id} offer {index}: duplicate URL")
            urls.add(url)
            try:
                _number(
                    offer.get("normalized_unit_price"),
                    "normalized_unit_price",
                    expense_id,
                )
            except ValueError as exc:
                errors.append(str(exc))
        if len(vendors) < min(3, len(offers)):
            errors.append(f"{expense_id}: offers must use distinct vendors")
    return errors


def _pack_text(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=PRICE_PACK["headers"])
    writer.writeheader()
    writer.writerows(rows)
    csv_text = output.getvalue()
    return (
        "===PREVIEW===\n"
        "Verified direct web offers for applicable house expenses.\n"
        "Freight is excluded when the product page requires a destination quote.\n"
        "===END_PREVIEW===\n"
        "===FILE: PRICE_PACK.csv===\n"
        f"{csv_text}"
        "===END_FILE===\n"
    )


def _rows(
    expenses: dict[str, dict[str, Any]],
    offers_by_expense: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for expense_id, offers in sorted(offers_by_expense.items()):
        expense = expenses[expense_id]
        ranked = sorted(
            offers,
            key=lambda offer: _number(
                offer["normalized_unit_price"],
                "normalized_unit_price",
                expense_id,
            ),
        )
        chosen = ranked
        for index, offer in enumerate(chosen, start=2):
            freight_unknown = offer.get("shipping_cost") in {None, ""}
            notes = [
                f"Preço exibido na fonte: {_text(offer.get('displayed_price'))}.",
                str(offer.get("evidence") or "").strip(),
            ]
            if freight_unknown:
                notes.append("Frete não incluído; depende do CEP de entrega.")
            ambiguity = str(offer.get("ambiguities") or "").strip()
            if ambiguity:
                notes.append(f"Ressalvas: {ambiguity}")
            rows.append(
                {
                    "id": expense_id,
                    "description": expense["description"],
                    "quotation_id": f"WEB_20260916_{index:02d}",
                    "unit_price": round(float(offer["normalized_unit_price"]), 4),
                    "quantity": 1,
                    "unit": expense["unit"],
                    "vendor": str(offer["vendor"]).strip(),
                    "shipping_cost": 0,
                    "total_price": round(float(offer["normalized_unit_price"]), 4),
                    "product_url": str(offer["url"]).strip(),
                    "price_notes": " ".join(note for note in notes if note),
                    "checked_at": "2026-09-16",
                    "selected": offer is chosen[0],
                    "currency": "BRL",
                    "brand": str(offer.get("brand") or "").strip(),
                    "model": str(offer.get("model") or "").strip(),
                    "specifications": (
                        str(offer.get("specifications") or "").strip()
                        or str(offer.get("_comparable_spec") or "").strip()
                    ),
                    "package_size": str(offer.get("package_size") or "").strip(),
                    "availability": str(offer.get("availability") or "").strip(),
                    "seller_location": str(offer.get("seller_location") or "").strip(),
                    "quote_valid_until": "",
                    "source_type": "text",
                    "source_name": str(offer.get("_research_file") or ""),
                    "source_page": "",
                    "extraction_confidence": 1,
                    "ambiguities": (f"{ambiguity}; " if ambiguity else "")
                    + (
                        "Frete desconhecido e excluído da comparação."
                        if freight_unknown
                        else ""
                    ),
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist the validated pack; otherwise only preview it.",
    )
    args = parser.parse_args()

    store = ExpenseStore(DATA_DIR)
    expenses = {item["id"]: item for item in store.list_expenses()}
    offers_by_expense, warnings = _offers_by_expense()
    errors = _validate_offers(expenses, offers_by_expense)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    rows = _rows(expenses, offers_by_expense)
    pack_text = _pack_text(rows)
    preview = preview_pack(pack_text)
    if not preview["ok"]:
        for error in preview.get("errors") or [preview.get("error")]:
            print(f"ERROR: {error}")
        return 1
    print(f"Validated {len(rows)} offers across {len(offers_by_expense)} expenses.")
    for warning in warnings:
        print(f"WARNING: {warning}")
    if not args.commit:
        print("Dry run only; pass --commit to persist and archive the pack.")
        return 0

    result = commit_rows(store, preview["rows"], pack_text=pack_text)
    if not result["ok"]:
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print(
        f"Imported {len(rows)} offers for {len(result['updated'])} expenses; "
        f"archived {result['archived']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
