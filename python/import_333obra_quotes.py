"""Merge, validate, and optionally import the Americana 333Obra price sweep."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESEARCH_DIR = DATA_DIR / "research"
SOURCE_DIR = RESEARCH_DIR / "333obra"
SCOPE_PATH = SOURCE_DIR / "scope.json"
CATALOG_PATH = RESEARCH_DIR / "333obra-lowest-prices.json"
CATALOG_MARKDOWN_PATH = RESEARCH_DIR / "333obra-lowest-prices.md"
sys.path.insert(0, str(ROOT / "python"))

from expense_store import ExpenseStore  # noqa: E402
from import_pipeline.pack_types import PRICE_PACK  # noqa: E402
from import_pipeline.pipeline import commit_rows, preview_pack  # noqa: E402
from persistence import atomic_write_text  # noqa: E402


ALLOWED_HOSTS = {"333obra.com.br", "www.333obra.com.br"}
LOCATION_BASIS = "americana_proxy_for_nova_odessa"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.name}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: root must be an object")
    return payload


def _number(value: Any, field: str, expense_id: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{expense_id}: invalid {field}: {value!r}") from exc
    if number <= 0:
        raise ValueError(f"{expense_id}: {field} must be positive")
    return round(number, 4)


def _text_list(value: Any) -> list[str]:
    values = value if isinstance(value, list) else ([value] if value else [])
    return [str(item).strip() for item in values if str(item).strip()]


def _serialized_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value or "").strip()


def _validate_url(value: Any, expense_id: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or not parsed.path.lower().endswith(".html")
    ):
        raise ValueError(
            f"{expense_id}: product_url must be a direct HTTPS 333Obra .html page"
        )
    if parsed.query or parsed.fragment:
        url = parsed._replace(query="", fragment="").geturl()
    return url


def _validate_winner(
    raw: dict[str, Any], expense: dict[str, Any], checked_at: str
) -> dict[str, Any]:
    expense_id = expense["id"]
    if not isinstance(raw, dict):
        raise ValueError(f"{expense_id}: winner must be an object")
    product_url = _validate_url(
        raw.get("final_url") or raw.get("product_url"), expense_id
    )
    source_url = _validate_url(raw.get("product_url") or product_url, expense_id)
    status = int(raw.get("http_status") or 0)
    if status != 200:
        raise ValueError(f"{expense_id}: winner URL was not verified with HTTP 200")
    location = str(raw.get("location_basis") or "").strip()
    if location != LOCATION_BASIS:
        raise ValueError(f"{expense_id}: missing Americana proxy location label")
    product = str(raw.get("matched_product") or "").strip()
    if not product:
        raise ValueError(f"{expense_id}: matched_product is required")
    normalized_price = _number(
        raw.get("normalized_unit_price_brl"),
        "normalized_unit_price_brl",
        expense_id,
    )
    displayed_price = _number(
        raw.get("displayed_price_brl"),
        "displayed_price_brl",
        expense_id,
    )
    minimum_quantity = int(raw.get("minimum_quantity") or 1)
    if minimum_quantity != 1:
        raise ValueError(
            f"{expense_id}: winner price must be purchasable at quantity 1"
        )
    freight = raw.get("freight_brl")
    if freight not in {None, ""}:
        freight = _number(freight, "freight_brl", expense_id)
    return {
        **raw,
        "matched_product": product,
        "displayed_price_brl": displayed_price,
        "normalized_unit_price_brl": normalized_price,
        "unit": str(expense.get("unit") or "").strip(),
        "minimum_quantity": 1,
        "bulk_tiers": (
            raw.get("bulk_tiers") if isinstance(raw.get("bulk_tiers"), list) else []
        ),
        "freight_brl": freight,
        "location_basis": LOCATION_BASIS,
        "checked_at": str(raw.get("checked_at") or checked_at)[:10],
        "product_url": source_url,
        "final_url": product_url,
        "http_status": 200,
        "verification_method": str(
            raw.get("verification_method") or "direct_product_page"
        ).strip(),
        "caveats": _text_list(raw.get("caveats")),
    }


def merge_catalog(store: ExpenseStore) -> dict[str, Any]:
    scope = _read_json(SCOPE_PATH)
    raw_clusters = scope.get("clusters")
    if not isinstance(raw_clusters, dict):
        raise ValueError("scope.json must contain clusters")
    expected_ids = [
        str(expense_id)
        for values in raw_clusters.values()
        for expense_id in (values if isinstance(values, list) else [])
    ]
    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("scope.json assigns an expense to multiple clusters")
    expense_map = {
        item["id"]: item
        for item in store.list_expenses()
        if item.get("record_type") == "material"
    }
    if set(expected_ids) != set(expense_map):
        missing = sorted(set(expense_map) - set(expected_ids))
        extra = sorted(set(expected_ids) - set(expense_map))
        raise ValueError(f"scope mismatch; missing={missing}; extra={extra}")

    by_id: dict[str, dict[str, Any]] = {}
    cluster_files = sorted(SOURCE_DIR.glob("cluster-*.json"))
    if not cluster_files:
        raise ValueError("no 333Obra cluster files were found")
    checked_dates: list[str] = []
    for path in cluster_files:
        document = _read_json(path)
        if document.get("location_basis") != LOCATION_BASIS:
            raise ValueError(f"{path.name}: invalid location_basis")
        checked_at = str(document.get("checked_at") or date.today().isoformat())[:10]
        checked_dates.append(checked_at)
        items = document.get("expenses")
        if not isinstance(items, list):
            raise ValueError(f"{path.name}: expenses must be a list")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{path.name}: expense entry must be an object")
            expense_id = str(item.get("expense_id") or "").strip()
            if expense_id not in expense_map:
                raise ValueError(f"{path.name}: unexpected expense {expense_id}")
            if expense_id in by_id:
                raise ValueError(f"{expense_id}: duplicated across cluster files")
            status = str(item.get("match_status") or "").strip()
            if status not in {"verified", "no_match"}:
                raise ValueError(
                    f"{expense_id}: match_status must be verified or no_match"
                )
            winner = None
            if status == "verified":
                winner = _validate_winner(
                    item.get("winner"), expense_map[expense_id], checked_at
                )
            by_id[expense_id] = {
                "expense_id": expense_id,
                "requested_item": expense_map[expense_id]["description"],
                "requested_unit": expense_map[expense_id]["unit"],
                "match_status": status,
                "winner": winner,
                "candidate_count": len(item.get("candidates") or []),
                "no_match_reason": str(item.get("no_match_reason") or "").strip(),
            }
    missing_results = sorted(set(expected_ids) - set(by_id))
    if missing_results:
        raise ValueError(f"cluster results missing expenses: {missing_results}")
    ordered = [by_id[expense_id] for expense_id in expected_ids]
    matched = sum(item["match_status"] == "verified" for item in ordered)
    return {
        "source": "333Obra",
        "source_url": "https://www.333obra.com.br/",
        "location_basis": LOCATION_BASIS,
        "checked_at": max(checked_dates),
        "summary": {
            "total_material_expenses": len(ordered),
            "verified_matches": matched,
            "no_match": len(ordered) - matched,
        },
        "expenses": ordered,
    }


def _pack_rows(catalog: dict[str, Any], store: ExpenseStore) -> list[dict[str, Any]]:
    expenses = {item["id"]: item for item in store.list_expenses()}
    rows = []
    for item in catalog["expenses"]:
        winner = item.get("winner")
        if not winner:
            continue
        expense_id = item["expense_id"]
        checked_at = winner["checked_at"]
        run_date = re.sub(r"[^0-9]", "", checked_at)[:8]
        caveats = list(winner["caveats"])
        caveats.append(
            "Preço de Americana/SP usado somente como proxy para Nova Odessa/SP."
        )
        if winner.get("freight_brl") is None:
            caveats.append("Frete para a obra não confirmado e não incluído.")
        seller = str(winner.get("seller") or "").strip()
        notes = [
            f"Produto: {winner['matched_product']}.",
            f"Preço exibido: R$ {winner['displayed_price_brl']:.2f}.",
            f"Local de referência: Americana/SP (proxy para Nova Odessa/SP).",
        ]
        if seller:
            notes.append(f"Vendedor anunciado: {seller}.")
        rows.append(
            {
                "id": expense_id,
                "description": expenses[expense_id]["description"],
                "quotation_id": f"333OBRA_AMERICANA_{run_date}",
                "unit_price": winner["normalized_unit_price_brl"],
                "quantity": 1,
                "unit": expenses[expense_id]["unit"],
                "vendor": "333Obra",
                "shipping_cost": winner.get("freight_brl") or 0,
                "total_price": round(
                    winner["normalized_unit_price_brl"]
                    + (winner.get("freight_brl") or 0),
                    2,
                ),
                "product_url": winner["final_url"],
                "price_notes": " ".join(notes),
                "checked_at": checked_at,
                "selected": False,
                "currency": "BRL",
                "brand": str(winner.get("brand") or ""),
                "model": str(winner.get("sku") or ""),
                "specifications": _serialized_text(
                    winner.get("specifications")
                ),
                "package_size": str(winner.get("package_size") or ""),
                "availability": str(winner.get("availability") or ""),
                "seller_location": "Americana/SP — proxy; entrega não confirmada",
                "quote_valid_until": "",
                "source_type": "text",
                "source_name": "333obra-lowest-prices.json",
                "source_page": "",
                "extraction_confidence": 1,
                "ambiguities": "; ".join(caveats),
            }
        )
    return rows


def _pack_text(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=PRICE_PACK["headers"])
    writer.writeheader()
    writer.writerows(rows)
    return (
        "===PREVIEW===\n"
        "Lowest verified 333Obra offers using Americana/SP as a Nova Odessa proxy.\n"
        "These quotations must not be auto-selected and exclude unknown freight.\n"
        "===END_PREVIEW===\n"
        "===FILE: PRICE_PACK.csv===\n"
        f"{output.getvalue()}"
        "===END_FILE===\n"
    )


def _markdown(catalog: dict[str, Any]) -> str:
    summary = catalog["summary"]
    lines = [
        "# 333Obra — menores preços verificados",
        "",
        "Referência regional: Americana/SP, usada somente como proxy para Nova Odessa/SP.",
        "Frete não foi considerado quando o site não apresentou um valor explícito.",
        "",
        f"- Materiais avaliados: {summary['total_material_expenses']}",
        f"- Correspondências verificadas: {summary['verified_matches']}",
        f"- Sem correspondência segura: {summary['no_match']}",
        "",
        "## Ofertas verificadas",
        "",
    ]
    for item in catalog["expenses"]:
        winner = item.get("winner")
        if not winner:
            continue
        lines.extend(
            [
                f"### {item['requested_item']}",
                f"- Produto: {winner['matched_product']}",
                f"- Menor preço normalizado: R$ {winner['normalized_unit_price_brl']:.2f} por {item['requested_unit']}",
                f"- Preço exibido: R$ {winner['displayed_price_brl']:.2f}",
                f"- Link direto: {winner['final_url']}",
                f"- Ressalvas: {'; '.join(winner['caveats']) or 'Somente a ressalva regional indicada acima.'}",
                "",
            ]
        )
    lines.extend(["## Sem correspondência segura", ""])
    for item in catalog["expenses"]:
        if item.get("winner"):
            continue
        lines.append(
            f"- {item['requested_item']}: {item['no_match_reason'] or 'Nenhuma oferta comparável com preço e URL verificáveis.'}"
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Import verified winners after merging and validating all clusters.",
    )
    args = parser.parse_args()
    store = ExpenseStore(DATA_DIR)
    catalog = merge_catalog(store)
    atomic_write_text(
        CATALOG_PATH,
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(CATALOG_MARKDOWN_PATH, _markdown(catalog))
    rows = _pack_rows(catalog, store)
    pack_text = _pack_text(rows)
    preview = preview_pack(pack_text)
    if not preview["ok"]:
        for error in preview.get("errors") or [preview.get("error")]:
            print(f"ERROR: {error}")
        return 1
    print(
        f"Validated {len(rows)} 333Obra winners across "
        f"{catalog['summary']['total_material_expenses']} material expenses."
    )
    if not args.commit:
        print("Dry run only; pass --commit to import without changing selections.")
        return 0
    result = commit_rows(
        store,
        preview["rows"],
        pack_text=pack_text,
        preview_digest=preview["preview_digest"],
        preserve_financial_state=True,
    )
    if not result["ok"]:
        for error in result.get("errors") or [result.get("error")]:
            print(f"ERROR: {error}")
        return 1
    print(
        f"Imported {len(rows)} unselected 333Obra quotations; "
        f"archived {Path(result['archived']).name}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
