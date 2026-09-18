"""Patch remaining gaps: kit sealants, fix wrong pia match, fill missing SKUs via API probes."""

from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import requests

DIR = Path(__file__).resolve().parent
CHECKED = date.today().isoformat()
LOCATION = "nova_odessa_cep_13380"
S = requests.Session()
S.headers.update(
    {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "X-Region": "campinas"}
)
API = "https://www.leroymerlin.com.br/api/v3/products/{}"


def fetch(pid: str) -> dict[str, Any] | None:
    r = S.get(API.format(pid), timeout=30)
    if r.status_code != 200:
        return None
    p = r.json()["data"]["product"]
    pricing = (p.get("pricing") or {}).get("price") or {}
    price = pricing.get("to")
    if price is None:
        to = (p.get("price") or {}).get("to") or {}
        if to.get("integers") is not None:
            price = float(f"{to['integers']}.{to.get('decimals') or '00'}")
    if not price:
        return None
    url = str(p.get("url") or "").split("?")[0]
    return {
        "name": p["name"],
        "sku": str(p["_id"]),
        "brand": p.get("brand") or "",
        "url": url,
        "price": float(price),
        "available": bool(p.get("isAvailableOnEcommerce")),
        "pack_price": (p.get("pack") or {}).get("price"),
        "packaging": (p.get("pack") or {}).get("packaging"),
    }


def cand(prod: dict[str, Any], unit: str, **extra: Any) -> dict[str, Any]:
    displayed = prod["price"]
    normalized = prod["price"]
    package = "1"
    caveats = ["Freight not calculated for CEP 13380-000; freight_brl left null."]
    name = prod["name"].lower()
    if extra.get("div"):
        div = extra["div"]
        package = extra.get("package", str(div))
        normalized = round(displayed / div, 4)
        caveats.insert(0, extra.get("caveat", f"Normalized by {div}."))
    return {
        "matched_product": prod["name"],
        "sku": prod["sku"],
        "seller": "Leroy Merlin",
        "specifications": {"brand": prod.get("brand") or ""},
        "package_size": package,
        "displayed_price_brl": round(displayed, 2),
        "normalized_unit_price_brl": round(normalized, 4),
        "unit": unit,
        "minimum_quantity": 1,
        "bulk_tiers": [],
        "freight_brl": None,
        "availability": "in_stock" if prod.get("available") else "limited",
        "location_basis": LOCATION,
        "checked_at": CHECKED,
        "product_url": prod["url"],
        "final_url": prod["url"],
        "http_status": 200,
        "verification_method": f"api/v3/products/{prod['sku']} HTTP 200 X-Region=campinas; {prod['url']}",
        "caveats": caveats,
    }


def set_expense(cluster: str, eid: str, entry: dict[str, Any]) -> None:
    path = DIR / f"cluster-{cluster}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    for i, e in enumerate(doc["expenses"]):
        if e["expense_id"] == eid:
            doc["expenses"][i] = entry
            break
    doc["checked_at"] = CHECKED
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def verified(
    eid: str, item: str, unit: str, candidates: list[dict], winner: dict | None = None
) -> dict:
    winner = winner or candidates[0]
    return {
        "expense_id": eid,
        "requested_item": item,
        "requested_unit": unit,
        "match_status": "verified",
        "candidates": candidates,
        "winner": winner,
        "no_match_reason": "",
    }


def main() -> None:
    # EXP_0048 kit from finishes cache component SKUs
    silicone_ids = ["1568648235", "1571928010", "1571505158"]
    espuma_ids = ["1568116649", "1572364358", "1571504289"]
    sil_cands, esp_cands = [], []
    for pid in silicone_ids:
        p = fetch(pid)
        time.sleep(0.15)
        if p and "silicone" in p["name"].lower():
            sil_cands.append(cand(p, "kit"))
    for pid in espuma_ids:
        p = fetch(pid)
        time.sleep(0.15)
        if p and "espuma" in p["name"].lower():
            esp_cands.append(cand(p, "kit"))
    sil_cands.sort(key=lambda x: x["normalized_unit_price_brl"])
    esp_cands.sort(key=lambda x: x["normalized_unit_price_brl"])
    if sil_cands and esp_cands:
        parts = [sil_cands[0], esp_cands[0]]
        total = round(sum(p["displayed_price_brl"] for p in parts), 2)
        winner = {
            **parts[0],
            "matched_product": "Kit representativo: "
            + " + ".join(p["matched_product"] for p in parts),
            "displayed_price_brl": total,
            "normalized_unit_price_brl": total,
            "package_size": "2 itens (silicone + espuma; selante PU não verificado)",
            "verification_method": f"Sum of silicone+espuma api/v3 prices = R${total:.2f}. PU sealant not found.",
            "caveats": [
                "Representative kit from lowest silicone + espuma; selante PU not verified in this run.",
                "Freight not calculated for CEP 13380-000; freight_brl left null.",
            ],
            "specifications": {
                "components": [
                    {
                        "name": p["matched_product"],
                        "price": p["displayed_price_brl"],
                        "url": p["final_url"],
                    }
                    for p in parts
                ]
            },
        }
        set_expense(
            "finishes",
            "EXP_0048",
            verified(
                "EXP_0048",
                "Silicone, espuma expansiva, selante PU",
                "kit",
                parts,
                winner,
            ),
        )
        print("patched EXP_0048", total)

    # EXP_0039: find cuba/pia inox — probe common ids from plumbing agent
    cuba_ids = [
        "1571710893",
        "1567475755",
        "1567408633",
        "1571384688",
        "1568949595",
        "1571161319",
    ]
    cuba_cands = []
    for pid in cuba_ids:
        p = fetch(pid)
        time.sleep(0.15)
        if not p:
            continue
        n = p["name"].lower()
        if ("cuba" in n or "pia" in n) and "torneira" not in n:
            cuba_cands.append(cand(p, "conjunto"))
    # also scan finishes-unrelated: search pool from transcript ids with cuba in name by fetching more
    more = ["1570549398", "1567096770", "1567392026", "1571419038", "1569855961"]
    for pid in more:
        p = fetch(pid)
        time.sleep(0.1)
        if p and "cuba" in p["name"].lower() and "torneira" not in p["name"].lower():
            cuba_cands.append(cand(p, "conjunto"))
    cuba_cands.sort(key=lambda x: x["normalized_unit_price_brl"])
    if cuba_cands:
        set_expense(
            "plumbing",
            "EXP_0039",
            verified("EXP_0039", "Pias e bancadas", "conjunto", cuba_cands),
        )
        print(
            "patched EXP_0039",
            cuba_cands[0]["normalized_unit_price_brl"],
            cuba_cands[0]["matched_product"][:50],
        )
    else:
        set_expense(
            "plumbing",
            "EXP_0039",
            {
                "expense_id": "EXP_0039",
                "requested_item": "Pias e bancadas",
                "requested_unit": "conjunto",
                "match_status": "no_match",
                "candidates": [],
                "winner": None,
                "no_match_reason": "No cuba/pia (non-faucet) product with verified API price in this run.",
            },
        )
        print("EXP_0039 no_match")

    # EXP_0037 sifao
    sifao_ids = ["1567512000", "1567515360", "1570851139", "1567879300"]
    sif = []
    for pid in sifao_ids:
        p = fetch(pid)
        time.sleep(0.15)
        if p and ("sif" in p["name"].lower()):
            sif.append(cand(p, "unidade"))
    sif.sort(key=lambda x: x["normalized_unit_price_brl"])
    if sif:
        set_expense(
            "plumbing",
            "EXP_0037",
            verified("EXP_0037", "Sifões e ralos", "unidade", sif),
        )
        print("patched EXP_0037", sif[0]["normalized_unit_price_brl"])

    # EXP_0031 smaller vitro — try ids near 1568113887
    vitro_ids = ["1568113887", "1567589117", "1567589121", "1567589156", "1566806473"]
    vitro = []
    for pid in vitro_ids:
        p = fetch(pid)
        time.sleep(0.15)
        if not p:
            continue
        n = p["name"].lower()
        if "basculante" in n or "vitro" in n or "vitrô" in n:
            # prefer smaller than 60x60 for bathroom
            vitro.append(cand(p, "unidade"))
    # pick cheapest that mentions 40 or 50 or 60x40
    bath = [c for c in vitro if re.search(r"40|50|45", c["matched_product"])]
    pick = bath or vitro
    pick.sort(key=lambda x: x["normalized_unit_price_brl"])
    if pick:
        # if only 60x60 available, still record with caveat for bathroom use
        winner = deepcopy(pick[0])
        if not bath:
            winner["caveats"] = [
                "Only ~60x60 basculante verified; used as bathroom vitrô proxy.",
                *winner.get("caveats", []),
            ]
        set_expense(
            "openings",
            "EXP_0031",
            verified("EXP_0031", "Vitrôs banheiros", "unidade", pick, winner),
        )
        print("patched EXP_0031", winner["normalized_unit_price_brl"])

    # Probe missing structural / electrical / fasteners / balcao / rodape / telha
    probes = {
        ("structural", "EXP_0017", "Telha", "unidade"): [
            # try search-like known ceramic tile ids if any in cache html
        ],
        ("structural", "EXP_0019", "Tijolinho de barro", "unidade"): [],
        ("structural", "EXP_0021", "Arame recozido", "quilograma (kg)"): [],
        ("openings", "EXP_0027", "Porta Balcão (R$2000)", "unidade"): [],
        ("electrical", "EXP_0033", "Quadro de distribuição", "unidade"): [],
        ("electrical", "EXP_0034", "Conduítes", "metro linear (m)"): [],
        ("electrical", "EXP_0035", "Lâmpadas", "unidade"): [],
        ("tools_logistics", "EXP_0047", "Pregos, parafusos, buchas", "pacote"): [],
        (
            "finishes",
            "EXP_0041",
            "Rodapés para acompanhar o porcelanato (R$1500)",
            "metro linear (m)",
        ): [
            "1572343516",
            "1571598281",
        ],
    }

    # Harvest ids from search debug html files by keyword
    html_blob = ""
    for p in (
        (DIR / "_tmp_search_debug").glob("*.html")
        if (DIR / "_tmp_search_debug").exists()
        else []
    ):
        html_blob += p.read_text(encoding="utf-8", errors="ignore")
    for p in DIR.glob("_tmp*.json"):
        html_blob += p.read_text(encoding="utf-8", errors="ignore")

    def ids_near(*words: str) -> list[str]:
        found = []
        for m in re.finditer(
            r"https://www\.leroymerlin\.com\.br/[a-z0-9,\|\-%]+_(\d{6,})",
            html_blob,
            re.I,
        ):
            start = max(0, m.start() - 200)
            ctx = html_blob[start : m.end() + 80].lower()
            if all(w.lower() in ctx for w in words):
                if m.group(1) not in found:
                    found.append(m.group(1))
        return found[:12]

    keyword_map = {
        ("structural", "EXP_0017", "Telha", "unidade"): (
            ["telha"],
            lambda n: "telha" in n and "cumeeira" not in n,
        ),
        ("structural", "EXP_0019", "Tijolinho de barro", "unidade"): (
            ["tijolo"],
            lambda n: "tijolo" in n,
        ),
        ("structural", "EXP_0021", "Arame recozido", "quilograma (kg)"): (
            ["arame", "recoz"],
            lambda n: "arame" in n and "recoz" in n,
        ),
        ("openings", "EXP_0027", "Porta Balcão (R$2000)", "unidade"): (
            ["porta", "balc"],
            lambda n: "porta" in n
            and ("balc" in n or ("correr" in n and "alumin" in n)),
        ),
        ("electrical", "EXP_0033", "Quadro de distribuição", "unidade"): (
            ["quadro"],
            lambda n: "quadro" in n and "distrib" in n,
        ),
        ("electrical", "EXP_0034", "Conduítes", "metro linear (m)"): (
            ["eletroduto"],
            lambda n: "eletroduto" in n or "corrug" in n,
        ),
        ("electrical", "EXP_0035", "Lâmpadas", "unidade"): (
            ["lampada"],
            lambda n: ("lampada" in n or "lâmpada" in n) and "led" in n,
        ),
        ("tools_logistics", "EXP_0047", "Pregos, parafusos, buchas", "pacote"): (
            ["parafuso"],
            lambda n: any(x in n for x in ("parafuso", "prego", "bucha")),
        ),
    }

    for key, (words, pred) in keyword_map.items():
        cluster, eid, item, unit = key
        ids = ids_near(*words)
        # also single-word looser
        if not ids and len(words) == 1:
            ids = ids_near(words[0])
        cands = []
        for pid in ids[:15]:
            p = fetch(pid)
            time.sleep(0.12)
            if p and pred(p["name"].lower()):
                extra = {}
                if eid == "EXP_0034":
                    m = re.search(r"(\d+)\s*m\b", p["name"].lower())
                    if m and int(m.group(1)) >= 5:
                        extra = {
                            "div": int(m.group(1)),
                            "package": f"{m.group(1)} m",
                            "caveat": f"Normalized from {m.group(1)} m roll.",
                        }
                if eid == "EXP_0019":
                    m = re.search(r"(\d+)\s*pe[cç]as", p["name"].lower())
                    if m and int(m.group(1)) > 1:
                        extra = {
                            "div": int(m.group(1)),
                            "package": f"{m.group(1)} peças",
                            "caveat": f"Pack of {m.group(1)}; per brick.",
                        }
                if eid == "EXP_0041":
                    m = re.search(r"(\d+(?:[.,]\d+)?)\s*m", p["name"].lower())
                    if (
                        "2,40" in p["name"]
                        or "2.40" in p["name"]
                        or "x2,40" in p["name"].lower()
                    ):
                        # 6 un x 2.40m master pack etc
                        if "6 un" in p["name"].lower() or "6un" in p[
                            "name"
                        ].lower().replace(" ", ""):
                            extra = {
                                "div": 6 * 2.4,
                                "package": "6x2,40m",
                                "caveat": "Normalized per meter from 6x2.40m pack.",
                            }
                        else:
                            extra = {
                                "div": 2.4,
                                "package": "2,40 m",
                                "caveat": "Normalized per meter from 2.40m piece.",
                            }
                cands.append(cand(p, unit, **extra))
        cands.sort(key=lambda x: x["normalized_unit_price_brl"])
        if cands:
            set_expense(cluster, eid, verified(eid, item, unit, cands))
            print(
                "patched",
                eid,
                cands[0]["normalized_unit_price_brl"],
                cands[0]["matched_product"][:55],
            )
        else:
            print("still missing", eid)

    # rodape explicit
    rod = []
    for pid in ["1572343516", "1571598281"]:
        p = fetch(pid)
        time.sleep(0.15)
        if p and "rodap" in p["name"].lower():
            extra = {}
            if "2,40" in p["name"] or "2.40" in p["name"]:
                if "6" in p["name"] and "un" in p["name"].lower():
                    extra = {
                        "div": 14.4,
                        "package": "6x2,40m",
                        "caveat": "Normalized per m from 6x2.40m pack.",
                    }
                else:
                    extra = {
                        "div": 2.4,
                        "package": "2,40 m",
                        "caveat": "Normalized per m from 2.40m piece.",
                    }
            rod.append(cand(p, "metro linear (m)", **extra))
    rod.sort(key=lambda x: x["normalized_unit_price_brl"])
    if rod:
        set_expense(
            "finishes",
            "EXP_0041",
            verified(
                "EXP_0041",
                "Rodapés para acompanhar o porcelanato (R$1500)",
                "metro linear (m)",
                rod,
            ),
        )
        print("patched EXP_0041", rod[0]["normalized_unit_price_brl"])


if __name__ == "__main__":
    main()
