"""Merge regional local-depo probes, cross-vendor winners, and cotação packs."""

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
SOURCE_DIR = RESEARCH_DIR / "regional-local"
SCOPE_PATH = SOURCE_DIR / "scope.json"
LOCAL_CATALOG_PATH = RESEARCH_DIR / "regional-local-lowest-prices.json"
LOCAL_CATALOG_MD_PATH = RESEARCH_DIR / "regional-local-lowest-prices.md"
CROSS_CATALOG_PATH = RESEARCH_DIR / "regional-cross-vendor-winners.json"
CROSS_CATALOG_MD_PATH = RESEARCH_DIR / "regional-cross-vendor-winners.md"
COTACAO_PACK_PATH = RESEARCH_DIR / "cotacao-whatsapp-pack.md"
sys.path.insert(0, str(ROOT / "python"))

from expense_store import ExpenseStore  # noqa: E402
from import_pipeline.pack_types import PRICE_PACK  # noqa: E402
from import_pipeline.pipeline import commit_rows, preview_pack  # noqa: E402
from persistence import atomic_write_text  # noqa: E402

LOCATION_BASIS = "nova_odessa_cep_13380"
CHAIN_FILES = {
    "leroymerlin": RESEARCH_DIR / "leroymerlin-lowest-prices.json",
    "sodimac": RESEARCH_DIR / "sodimac-lowest-prices.json",
    "telhanorte": RESEARCH_DIR / "telhanorte-lowest-prices.json",
    "333obra": RESEARCH_DIR / "333obra-lowest-prices.json",
}
CHAIN_DISPLAY = {
    "leroymerlin": "Leroy Merlin",
    "sodimac": "Sodimac Brasil",
    "telhanorte": "Telhanorte",
    "333obra": "333Obra",
}


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


def _vendor_map(scope: dict[str, Any]) -> dict[str, dict[str, Any]]:
    vendors = scope.get("vendors")
    if not isinstance(vendors, list) or not vendors:
        raise ValueError("scope.json must list vendors")
    out: dict[str, dict[str, Any]] = {}
    for vendor in vendors:
        if not isinstance(vendor, dict):
            raise ValueError("vendor entries must be objects")
        vendor_id = str(vendor.get("id") or "").strip()
        if not vendor_id:
            raise ValueError("vendor missing id")
        out[vendor_id] = vendor
    return out


def _validate_local_winner(
    raw: dict[str, Any],
    expense: dict[str, Any],
    vendor: dict[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    expense_id = expense["id"]
    if not isinstance(raw, dict):
        raise ValueError(f"{expense_id}: winner must be an object")
    allowed = {
        str(host).strip().lower()
        for host in (vendor.get("allowed_hosts") or [])
        if str(host).strip()
    }
    if not allowed:
        raise ValueError(
            f"{expense_id}: vendor {vendor['id']} has no allowed_hosts for site_verified"
        )
    product_url = str(raw.get("final_url") or raw.get("product_url") or "").strip()
    source_url = str(raw.get("product_url") or product_url).strip()
    for label, url in (("final_url", product_url), ("product_url", source_url)):
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or host not in allowed:
            raise ValueError(
                f"{expense_id}: {label} must be HTTPS on allowed host for {vendor['id']}"
            )
    status = int(raw.get("http_status") or 0)
    if status != 200:
        raise ValueError(f"{expense_id}: winner URL was not verified with HTTP 200")
    if str(raw.get("location_basis") or "").strip() != LOCATION_BASIS:
        raise ValueError(f"{expense_id}: missing Nova Odessa CEP location label")
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
        "seller": str(raw.get("seller") or vendor.get("name") or "").strip(),
        "vendor_id": vendor["id"],
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
        "price_evidence": "site_verified",
        "verification_method": str(
            raw.get("verification_method") or "direct_product_page"
        ).strip(),
        "caveats": _text_list(raw.get("caveats")),
    }


def merge_local_catalog(store: ExpenseStore) -> dict[str, Any]:
    scope = _read_json(SCOPE_PATH)
    vendors = _vendor_map(scope)
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
        raise ValueError("no regional-local cluster files were found")
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
            vendor_results = item.get("vendor_results")
            if not isinstance(vendor_results, list) or not vendor_results:
                raise ValueError(f"{expense_id}: vendor_results required")
            normalized_results: list[dict[str, Any]] = []
            verified_winners: list[dict[str, Any]] = []
            cotacao_vendors: list[str] = []
            for result in vendor_results:
                if not isinstance(result, dict):
                    raise ValueError(f"{expense_id}: vendor_result must be an object")
                vendor_id = str(result.get("vendor_id") or "").strip()
                if vendor_id not in vendors:
                    raise ValueError(f"{expense_id}: unknown vendor_id {vendor_id}")
                status = str(result.get("match_status") or "").strip()
                if status not in {"verified", "no_match"}:
                    raise ValueError(
                        f"{expense_id}/{vendor_id}: match_status must be verified or no_match"
                    )
                evidence = str(result.get("price_evidence") or "").strip()
                if evidence not in {
                    "site_verified",
                    "reputation_only",
                    "cotacao_needed",
                }:
                    raise ValueError(
                        f"{expense_id}/{vendor_id}: invalid price_evidence {evidence!r}"
                    )
                winner = None
                if status == "verified":
                    if evidence != "site_verified":
                        raise ValueError(
                            f"{expense_id}/{vendor_id}: verified requires site_verified"
                        )
                    winner = _validate_local_winner(
                        result.get("winner") or {},
                        expense_map[expense_id],
                        vendors[vendor_id],
                        checked_at,
                    )
                    verified_winners.append(winner)
                if result.get("cotacao_needed") or status == "no_match":
                    cotacao_vendors.append(vendor_id)
                normalized_results.append(
                    {
                        "vendor_id": vendor_id,
                        "vendor_name": vendors[vendor_id]["name"],
                        "tier": vendors[vendor_id].get("tier"),
                        "match_status": status,
                        "price_evidence": evidence,
                        "no_match_reason": str(
                            result.get("no_match_reason") or ""
                        ).strip(),
                        "cotacao_needed": bool(
                            result.get("cotacao_needed") or status == "no_match"
                        ),
                        "candidate_count": len(result.get("candidates") or []),
                        "winner": winner,
                    }
                )
            verified_winners.sort(key=lambda row: row["normalized_unit_price_brl"])
            best = verified_winners[0] if verified_winners else None
            by_id[expense_id] = {
                "expense_id": expense_id,
                "requested_item": expense_map[expense_id]["description"],
                "requested_unit": expense_map[expense_id]["unit"],
                "match_status": "verified" if best else "no_match",
                "price_evidence": "site_verified" if best else "cotacao_needed",
                "winner": best,
                "verified_vendor_count": len(verified_winners),
                "vendor_results": normalized_results,
                "cotacao_vendor_ids": sorted(set(cotacao_vendors)),
                "no_match_reason": (
                    "" if best else "no_public_sku_on_probed_local_depos"
                ),
            }
    missing_results = sorted(set(expected_ids) - set(by_id))
    if missing_results:
        raise ValueError(f"cluster results missing expenses: {missing_results}")
    ordered = [by_id[expense_id] for expense_id in expected_ids]
    matched = sum(item["match_status"] == "verified" for item in ordered)
    return {
        "source": "Regional local depos",
        "source_report": "data/research/regional-vendors-report.json",
        "location_basis": LOCATION_BASIS,
        "checked_at": max(checked_dates),
        "summary": {
            "total_material_expenses": len(ordered),
            "verified_matches": matched,
            "no_match": len(ordered) - matched,
            "vendors_probed": len(vendors),
        },
        "vendors": [
            {
                "id": vendor["id"],
                "name": vendor["name"],
                "tier": vendor.get("tier"),
                "cities": vendor.get("cities") or [],
                "phone": vendor.get("phone"),
                "url": vendor.get("url"),
            }
            for vendor in scope["vendors"]
        ],
        "expenses": ordered,
    }


def _chain_winners() -> dict[str, dict[str, dict[str, Any]]]:
    """expense_id -> chain_id -> winner summary."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for chain_id, path in CHAIN_FILES.items():
        if not path.exists():
            continue
        catalog = _read_json(path)
        for item in catalog.get("expenses") or []:
            if not isinstance(item, dict):
                continue
            if item.get("match_status") != "verified" or not item.get("winner"):
                continue
            expense_id = str(item.get("expense_id") or "").strip()
            winner = item["winner"]
            out.setdefault(expense_id, {})[chain_id] = {
                "vendor_id": chain_id,
                "vendor_name": CHAIN_DISPLAY.get(chain_id, chain_id),
                "vendor_type": "chain",
                "matched_product": winner.get("matched_product"),
                "normalized_unit_price_brl": float(winner["normalized_unit_price_brl"]),
                "displayed_price_brl": float(winner.get("displayed_price_brl") or 0),
                "product_url": winner.get("final_url") or winner.get("product_url"),
                "checked_at": winner.get("checked_at"),
                "source_file": path.name,
            }
    return out


def build_cross_vendor(
    local_catalog: dict[str, Any], store: ExpenseStore
) -> dict[str, Any]:
    scope = _read_json(SCOPE_PATH)
    vendors = _vendor_map(scope)
    chain_by_expense = _chain_winners()
    expense_map = {
        item["id"]: item
        for item in store.list_expenses()
        if item.get("record_type") == "material"
    }
    rows: list[dict[str, Any]] = []
    for item in local_catalog["expenses"]:
        expense_id = item["expense_id"]
        expense = expense_map[expense_id]
        offers: list[dict[str, Any]] = []
        for chain_id, offer in (chain_by_expense.get(expense_id) or {}).items():
            offers.append(offer)
        if item.get("winner"):
            winner = item["winner"]
            offers.append(
                {
                    "vendor_id": winner["vendor_id"],
                    "vendor_name": winner.get("seller")
                    or vendors[winner["vendor_id"]]["name"],
                    "vendor_type": "local_depo",
                    "matched_product": winner["matched_product"],
                    "normalized_unit_price_brl": winner["normalized_unit_price_brl"],
                    "displayed_price_brl": winner["displayed_price_brl"],
                    "product_url": winner["final_url"],
                    "checked_at": winner["checked_at"],
                    "source_file": "regional-local-lowest-prices.json",
                }
            )
        offers.sort(key=lambda row: row["normalized_unit_price_brl"])
        best = offers[0] if offers else None
        pending = [
            {
                "vendor_id": vendor_id,
                "vendor_name": vendors[vendor_id]["name"],
                "tier": vendors[vendor_id].get("tier"),
                "phone": vendors[vendor_id].get("phone"),
                "url": vendors[vendor_id].get("url"),
            }
            for vendor_id in item.get("cotacao_vendor_ids") or []
            if vendor_id in vendors
        ]
        # Prefer Tier-A first in pending list
        pending.sort(
            key=lambda row: (0 if row.get("tier") == "A" else 1, row["vendor_name"])
        )
        rows.append(
            {
                "expense_id": expense_id,
                "requested_item": expense["description"],
                "requested_unit": expense["unit"],
                "verified_offer_count": len(offers),
                "overall_winner": best,
                "status": "verified" if best else "pending_cotacao",
                "pending_cotacao": pending if not item.get("winner") else pending[:3],
                "all_verified_offers": offers,
                "local_match_status": item["match_status"],
                "notes": (
                    "Lowest among verified chain catalogs + any site_verified local depo prices."
                    if best
                    else "No verified price from chains or local depos; use cotação pack."
                ),
            }
        )
    verified = sum(1 for row in rows if row["status"] == "verified")
    return {
        "title": "Regional cross-vendor verified winners",
        "location_basis": LOCATION_BASIS,
        "checked_at": local_catalog["checked_at"],
        "method": {
            "chains": "Reuse *-lowest-prices.json catalogs (no re-scrape).",
            "local_depos": "Probe results from data/research/regional-local/cluster-*.json.",
            "ranking": "Lowest normalized_unit_price_brl among verified offers only.",
        },
        "summary": {
            "total_material_expenses": len(rows),
            "verified_overall_winners": verified,
            "pending_cotacao_only": len(rows) - verified,
            "local_site_verified": local_catalog["summary"]["verified_matches"],
        },
        "expenses": rows,
    }


def build_cotacao_pack(local_catalog: dict[str, Any], scope: dict[str, Any]) -> str:
    vendors = _vendor_map(scope)
    by_vendor: dict[str, list[dict[str, Any]]] = {v: [] for v in vendors}
    for item in local_catalog["expenses"]:
        for vendor_id in item.get("cotacao_vendor_ids") or []:
            if vendor_id not in by_vendor:
                continue
            # Tier-A: all expenses; Tier-B: only if already listed in vendor_results
            by_vendor[vendor_id].append(item)

    lines = [
        "# Pacote de cotação WhatsApp — depos regionais",
        "",
        "CEP da obra: **13380-000 (Nova Odessa/SP)**.",
        "Gerado automaticamente a partir do probe regional-local (2026-09-17).",
        "Nenhum depósito local teve SKU com preço público verificável neste passe.",
        "Copie a mensagem, ajuste quantidades e envie.",
        "",
    ]
    for vendor in scope["vendors"]:
        vendor_id = vendor["id"]
        items = by_vendor.get(vendor_id) or []
        if not items:
            continue
        # Deduplicate and limit Tier-B to fit_for_expenses + structural basics if huge
        if vendor.get("tier") == "B":
            fit = set(vendor.get("fit_for_expenses") or [])
            priority = set(scope.get("priority_gaps") or [])
            structural_basics = {"EXP_0015", "EXP_0016", "EXP_0019"}
            items = [
                item
                for item in items
                if item["expense_id"] in fit
                or item["expense_id"] in priority
                or item["expense_id"] in structural_basics
            ]
            if not items:
                continue
        phone = vendor.get("phone") or "(telefone não listado — buscar no Maps)"
        lines.extend(
            [
                f"## {vendor['name']}",
                f"- Cidade: {', '.join(vendor.get('cities') or [])}",
                f"- Tier: {vendor.get('tier')}",
                f"- Telefone/WhatsApp: {phone}",
                f"- Site/ref: {vendor.get('url') or '—'}",
                "",
                "### Mensagem sugerida",
                "",
                "```",
                f"Olá, sou de Nova Odessa (CEP 13380) e gostaria de cotação para obra:",
                "",
            ]
        )
        for item in items:
            lines.append(
                f"- {item['expense_id']}: {item['requested_item']} "
                f"(unidade: {item['requested_unit']}) — qtd: ___ "
            )
        lines.extend(
            [
                "",
                "Podem informar preço unitário, disponibilidade e frete/retirada para Nova Odessa?",
                "Obrigado!",
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Observações",
            "",
            "- Confrontar respostas com winners das redes em `regional-cross-vendor-winners.json`.",
            "- Só preferir o depósito local se a cotação for ≤ preço normalizado da rede para a mesma especificação.",
            "- EXP_0015 (areia/pedrisco m³): priorizar Ouro Verde e similares — redes não têm m³.",
            "",
        ]
    )
    return "\n".join(lines)


def _local_markdown(catalog: dict[str, Any]) -> str:
    summary = catalog["summary"]
    lines = [
        "# Depósitos locais — menores preços verificados",
        "",
        "Referência: CEP 13380-000 (Nova Odessa/SP).",
        "Somente preços com URL no domínio do próprio depósito.",
        "",
        f"- Materiais avaliados: {summary['total_material_expenses']}",
        f"- Correspondências site_verified: {summary['verified_matches']}",
        f"- Sem SKU público (cotação necessária): {summary['no_match']}",
        f"- Depósitos no escopo: {summary['vendors_probed']}",
        "",
    ]
    if summary["verified_matches"]:
        lines.extend(["## Ofertas verificadas", ""])
        for item in catalog["expenses"]:
            winner = item.get("winner")
            if not winner:
                continue
            lines.extend(
                [
                    f"### {item['requested_item']}",
                    f"- Depósito: {winner.get('seller')}",
                    f"- Produto: {winner['matched_product']}",
                    f"- Preço normalizado: R$ {winner['normalized_unit_price_brl']:.2f} / {item['requested_unit']}",
                    f"- Link: {winner['final_url']}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "## Resultado deste passe",
                "",
                "Nenhum depósito local publicou SKU com preço verificável.",
                "Use [`cotacao-whatsapp-pack.md`](cotacao-whatsapp-pack.md) e compare com as redes em "
                "[`regional-cross-vendor-winners.md`](regional-cross-vendor-winners.md).",
                "",
            ]
        )
    lines.extend(["## Itens sem preço local público", ""])
    for item in catalog["expenses"]:
        if item.get("winner"):
            continue
        lines.append(
            f"- {item['expense_id']} {item['requested_item']}: {item['no_match_reason']}"
        )
    return "\n".join(lines).rstrip() + "\n"


def _cross_markdown(catalog: dict[str, Any]) -> str:
    summary = catalog["summary"]
    lines = [
        "# Cross-vendor — menores preços verificados (redes + depos locais)",
        "",
        "CEP 13380-000. Redes reutilizam catálogos existentes; locais só entram se `site_verified`.",
        "",
        f"- Materiais: {summary['total_material_expenses']}",
        f"- Winners verificados: {summary['verified_overall_winners']}",
        f"- Só cotação pendente: {summary['pending_cotacao_only']}",
        f"- Locais site_verified neste passe: {summary['local_site_verified']}",
        "",
        "## Winners",
        "",
    ]
    for item in catalog["expenses"]:
        winner = item.get("overall_winner")
        if not winner:
            pending = ", ".join(
                row["vendor_name"] for row in (item.get("pending_cotacao") or [])[:4]
            )
            lines.append(
                f"- **{item['requested_item']}**: pending cotação"
                + (f" → {pending}" if pending else "")
            )
            continue
        lines.append(
            f"- **{item['requested_item']}**: "
            f"R$ {winner['normalized_unit_price_brl']:.2f} @ {winner['vendor_name']} "
            f"— {winner.get('product_url')}"
        )
    return "\n".join(lines).rstrip() + "\n"


def _pack_rows(
    local_catalog: dict[str, Any], store: ExpenseStore
) -> list[dict[str, Any]]:
    expenses = {item["id"]: item for item in store.list_expenses()}
    rows = []
    for item in local_catalog["expenses"]:
        winner = item.get("winner")
        if not winner:
            continue
        expense_id = item["expense_id"]
        checked_at = winner["checked_at"]
        run_date = re.sub(r"[^0-9]", "", checked_at)[:8]
        caveats = list(winner.get("caveats") or [])
        caveats.append(
            "Preço referenciado para CEP 13380-000 (Nova Odessa/SP); confirmar frete no depósito."
        )
        if winner.get("freight_brl") is None:
            caveats.append("Frete para a obra não confirmado e não incluído.")
        notes = [
            f"Produto: {winner['matched_product']}.",
            f"Preço exibido: R$ {winner['displayed_price_brl']:.2f}.",
            "Local de referência: CEP 13380-000 — Nova Odessa/SP.",
            f"Vendedor: {winner.get('seller') or ''}.",
        ]
        rows.append(
            {
                "id": expense_id,
                "description": expenses[expense_id]["description"],
                "quotation_id": f"REGIONAL_LOCAL_{run_date}",
                "unit_price": winner["normalized_unit_price_brl"],
                "quantity": 1,
                "unit": expenses[expense_id]["unit"],
                "vendor": str(winner.get("seller") or "Depósito regional"),
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
                "specifications": _serialized_text(winner.get("specifications")),
                "package_size": str(winner.get("package_size") or ""),
                "availability": str(winner.get("availability") or ""),
                "seller_location": "CEP 13380-000 Nova Odessa/SP — frete não confirmado",
                "quote_valid_until": "",
                "source_type": "text",
                "source_name": "regional-local-lowest-prices.json",
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
        "Site-verified regional local-depo offers for CEP 13380-000 (Nova Odessa/SP).\n"
        "These quotations must not be auto-selected and exclude unknown freight.\n"
        "===END_PREVIEW===\n"
        "===FILE: PRICE_PACK.csv===\n"
        f"{output.getvalue()}"
        "===END_FILE===\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--import",
        dest="do_import",
        action="store_true",
        help="Import site_verified local winners into quotations.json.",
    )
    parser.add_argument(
        "--commit",
        dest="do_import",
        action="store_true",
        help="Alias for --import.",
    )
    args = parser.parse_args()
    store = ExpenseStore(DATA_DIR)
    scope = _read_json(SCOPE_PATH)
    local_catalog = merge_local_catalog(store)
    cross_catalog = build_cross_vendor(local_catalog, store)
    cotacao = build_cotacao_pack(local_catalog, scope)

    atomic_write_text(
        LOCAL_CATALOG_PATH,
        json.dumps(local_catalog, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(LOCAL_CATALOG_MD_PATH, _local_markdown(local_catalog))
    atomic_write_text(
        CROSS_CATALOG_PATH,
        json.dumps(cross_catalog, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(CROSS_CATALOG_MD_PATH, _cross_markdown(cross_catalog))
    atomic_write_text(COTACAO_PACK_PATH, cotacao)

    rows = _pack_rows(local_catalog, store)

    print(
        f"Local catalog: {local_catalog['summary']['verified_matches']} site_verified / "
        f"{local_catalog['summary']['total_material_expenses']} expenses."
    )
    print(
        f"Cross-vendor: {cross_catalog['summary']['verified_overall_winners']} verified winners; "
        f"{cross_catalog['summary']['pending_cotacao_only']} pending cotação-only."
    )
    print(f"Wrote {COTACAO_PACK_PATH.name}")

    if not rows:
        print("No site_verified local winners; quotations.json unchanged.")
        return 0

    pack_text = _pack_text(rows)
    preview = preview_pack(pack_text)
    if not preview["ok"]:
        for error in preview.get("errors") or [preview.get("error")]:
            print(f"ERROR: {error}")
        return 1

    if not args.do_import:
        print("Dry run only; pass --import to import site_verified local winners.")
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
        f"Imported {len(rows)} unselected regional-local quotations; "
        f"archived {Path(result['archived']).name}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
