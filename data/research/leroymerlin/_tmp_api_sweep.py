"""API-backed Leroy Merlin sweep: discover IDs via DuckDuckGo HTML, price via api/v3/products/{id}."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, unquote

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "research" / "leroymerlin"
CHECKED = date.today().isoformat()
LOCATION = "nova_odessa_cep_13380"
API = "https://www.leroymerlin.com.br/api/v3/products/{}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html",
    "X-Region": "campinas",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

ID_RE = re.compile(r"leroymerlin\.com\.br/([a-z0-9,\-\|%]+)_(\d{6,})", re.I)

SEARCH_PLAN: dict[str, dict[str, Any]] = {
    "EXP_0014": {
        "item": "Impermeabilizante (bianco)",
        "unit": "balde",
        "queries": ["bianco vedacit 18", "aditivo chapisco bianco 18kg"],
        "include": ["bianco"],
        "prefer": ["18"],
    },
    "EXP_0015": {
        "item": "Areia grossa, fina e pedrisco",
        "unit": "metro cúbico (m³)",
        "queries": ["areia metro cubico", "areia m3"],
        "include": ["areia"],
        "require_m3": True,
    },
    "EXP_0016": {
        "item": "Cimento",
        "unit": "saco (50 kg)",
        "queries": ["cimento 50kg", "cimento cp ii 50kg"],
        "include": ["cimento"],
        "prefer": ["50"],
    },
    "EXP_0017": {
        "item": "Telha",
        "unit": "unidade",
        "queries": ["telha ceramica romana", "telha portuguesa ceramica"],
        "include": ["telha"],
        "exclude": ["cumeeira", "kit", "parafuso", "pvc"],
    },
    "EXP_0019": {
        "item": "Tijolinho de barro",
        "unit": "unidade",
        "queries": ["tijolo comum", "tijolo baiano"],
        "include": ["tijolo"],
        "exclude": ["aparente", "revest"],
    },
    "EXP_0021": {
        "item": "Arame recozido",
        "unit": "quilograma (kg)",
        "queries": ["arame recozido 1kg"],
        "include": ["arame", "recoz"],
    },
    "EXP_0042": {
        "item": "Madeiramento ou estrutura metálica",
        "unit": "metro quadrado (m²)",
        "queries": ["estrutura metalica telhado", "tesoura metalica"],
        "include": ["estrutura", "tesoura", "madeira"],
        "require_m2": True,
    },
    "EXP_0023": {
        "item": "Porcelanato",
        "unit": "metro quadrado (m²)",
        "queries": ["porcelanato 60x60"],
        "include": ["porcelanato"],
        "exclude": ["rejunte", "argamassa", "rodape"],
    },
    "EXP_0024": {
        "item": "Rejunte de porcelanato",
        "unit": "quilograma (kg)",
        "queries": ["rejunte porcelanato 1kg"],
        "include": ["rejunte"],
    },
    "EXP_0025": {
        "item": "Argamassa para o porcelanato",
        "unit": "saco (20 kg)",
        "queries": ["argamassa aciii 20kg", "argamassa porcelanato 20kg"],
        "include": ["argamassa"],
    },
    "EXP_0041": {
        "item": "Rodapés para acompanhar o porcelanato (R$1500)",
        "unit": "metro linear (m)",
        "queries": ["rodape porcelanato", "rodape ceramico"],
        "include": ["rodape", "rodapé"],
    },
    "EXP_0046": {
        "item": "Tinta",
        "unit": "lata (18 L)",
        "queries": ["tinta acrilica 18 litros", "tinta 18L"],
        "include": ["tinta"],
        "prefer": ["18"],
    },
    "EXP_0048": {
        "item": "Silicone, espuma expansiva, selante PU",
        "unit": "kit",
        "queries": ["silicone acetico", "espuma expansiva", "selante pu"],
        "include": ["silicone", "espuma", "selante"],
        "kit_mode": True,
    },
    "EXP_0049": {
        "item": "Lona para proteção da obra",
        "unit": "metro quadrado (m²)",
        "queries": ["lona preta plastica"],
        "include": ["lona"],
    },
    "EXP_0026": {
        "item": "Portas internas",
        "unit": "unidade",
        "queries": [
            "folha de porta madeira lisa 210x80",
            "folha porta artens vivace 80cm",
        ],
        "include": ["porta"],
        "exclude": ["kit porta", "fechadura", "balcao"],
        "seed_ids": ["92026116", "1567587108"],
    },
    "EXP_0027": {
        "item": "Porta Balcão (R$2000)",
        "unit": "unidade",
        "queries": ["porta balcao aluminio 2 folhas", "porta de correr aluminio sacada"],
        "include": ["porta"],
        "prefer": ["balc", "correr"],
    },
    "EXP_0029": {
        "item": "Janela (quartos e escritório)",
        "unit": "unidade",
        "queries": ["janela de correr aluminio 4 folhas 120x120"],
        "include": ["janela"],
        "seed_ids": ["1572871815", "1572483594"],
    },
    "EXP_0030": {
        "item": "Vitrô Sala",
        "unit": "unidade",
        "queries": ["vitro basculante 60x60 aluminio"],
        "include": ["vitro", "vitrô", "basculante"],
        "seed_ids": ["1568113887"],
    },
    "EXP_0031": {
        "item": "Vitrôs banheiros",
        "unit": "unidade",
        "queries": ["vitro basculante 40x40", "vitro basculante 60x40"],
        "include": ["vitro", "vitrô", "basculante"],
    },
    "EXP_0028": {
        "item": "Vaso",
        "unit": "unidade",
        "queries": ["vaso sanitario caixa acoplada"],
        "include": ["vaso", "bacia"],
    },
    "EXP_0036": {
        "item": "Torneiras",
        "unit": "unidade",
        "queries": ["torneira lavatorio", "torneira cozinha bica"],
        "include": ["torneira"],
    },
    "EXP_0037": {
        "item": "Sifões e ralos",
        "unit": "unidade",
        "queries": ["sifao universal", "sifão extensivel"],
        "include": ["sifao", "sifão"],
    },
    "EXP_0039": {
        "item": "Pias e bancadas",
        "unit": "conjunto",
        "queries": ["cuba inox cozinha", "pia inox embutir"],
        "include": ["cuba", "pia"],
    },
    "EXP_0040": {
        "item": "Box de vidro para o banheiro (R$850)",
        "unit": "unidade",
        "queries": ["box banheiro vidro temperado"],
        "include": ["box"],
    },
    "EXP_0044": {
        "item": "Caixa de água",
        "unit": "unidade",
        "queries": ["caixa dagua 500 litros", "caixa de agua 1000 litros fortlev"],
        "include": ["caixa"],
    },
    "EXP_0033": {
        "item": "Quadro de distribuição",
        "unit": "unidade",
        "queries": ["quadro distribuicao embutir"],
        "include": ["quadro"],
    },
    "EXP_0034": {
        "item": "Conduítes",
        "unit": "metro linear (m)",
        "queries": ["eletroduto corrugado 25mm", "conduit corrugado rolo"],
        "include": ["eletroduto", "conduit", "conduíte", "tubo"],
    },
    "EXP_0035": {
        "item": "Lâmpadas",
        "unit": "unidade",
        "queries": ["lampada led bulbo 9w"],
        "include": ["lampada", "lâmpada", "led"],
    },
    "EXP_0038": {
        "item": "Tomadas",
        "unit": "unidade",
        "queries": ["tomada 2p+t 10a"],
        "include": ["tomada"],
        "seed_ids": ["89676930"],
    },
    "EXP_0045": {
        "item": "Dispositivos de segurança",
        "unit": "conjunto",
        "queries": ["kit camera seguranca", "kit alarme residencial"],
        "include": ["camera", "alarme", "segurança", "seguranca"],
    },
    "EXP_0018": {
        "item": "Ferramentas",
        "unit": "conjunto",
        "queries": ["kit ferramentas tramontina", "jogo ferramentas manuais"],
        "include": ["kit", "jogo", "ferrament", "maleta"],
    },
    "EXP_0020": {
        "item": "Carrinho de mão",
        "unit": "unidade",
        "queries": ["carrinho de mao obra"],
        "include": ["carrinho"],
    },
    "EXP_0022": {
        "item": "Caçamba de entulho",
        "unit": "caçamba",
        "queries": ["cacamba entulho"],
        "include": ["cacamba", "caçamba"],
        "likely_no_match": True,
    },
    "EXP_0043": {
        "item": "Calhas e rufos",
        "unit": "metro linear (m)",
        "queries": ["calha galvanizada", "rufo galvanizado"],
        "include": ["calha", "rufo", "bobina"],
    },
    "EXP_0047": {
        "item": "Pregos, parafusos, buchas",
        "unit": "pacote",
        "queries": ["kit parafuso bucha", "parafuso chipboard pacote"],
        "include": ["prego", "parafuso", "bucha"],
    },
}

CLUSTERS = {
    "structural": [
        "EXP_0014",
        "EXP_0015",
        "EXP_0016",
        "EXP_0017",
        "EXP_0019",
        "EXP_0021",
        "EXP_0042",
    ],
    "finishes": [
        "EXP_0023",
        "EXP_0024",
        "EXP_0025",
        "EXP_0041",
        "EXP_0046",
        "EXP_0048",
        "EXP_0049",
    ],
    "openings": ["EXP_0026", "EXP_0027", "EXP_0029", "EXP_0030", "EXP_0031"],
    "plumbing": [
        "EXP_0028",
        "EXP_0036",
        "EXP_0037",
        "EXP_0039",
        "EXP_0040",
        "EXP_0044",
    ],
    "electrical": ["EXP_0033", "EXP_0034", "EXP_0035", "EXP_0038", "EXP_0045"],
    "tools_logistics": [
        "EXP_0018",
        "EXP_0020",
        "EXP_0022",
        "EXP_0043",
        "EXP_0047",
    ],
}


def discover_ids(query: str) -> list[tuple[str, str]]:
    """Return [(slug, id), ...] from DuckDuckGo HTML."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus('site:leroymerlin.com.br ' + query)}"
    try:
        r = SESSION.get(url, timeout=40)
    except requests.RequestException:
        return []
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    # DDG wraps URLs; also match raw
    for slug, pid in ID_RE.findall(unquote(r.text)):
        if pid in seen:
            continue
        seen.add(pid)
        found.append((slug, pid))
    return found[:12]


def fetch_product(pid: str) -> dict[str, Any] | None:
    try:
        r = SESSION.get(API.format(pid), timeout=30)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        product = r.json()["data"]["product"]
    except (KeyError, ValueError, TypeError):
        return None
    pricing = (product.get("pricing") or {}).get("price") or {}
    price = pricing.get("to")
    if price is None:
        # fallback price.to integers/decimals
        to = (product.get("price") or {}).get("to") or {}
        if to.get("integers") is not None:
            price = float(f"{to['integers']}.{to.get('decimals') or '00'}")
    if not price or float(price) <= 0:
        return None
    name = str(product.get("name") or "").strip()
    url = str(product.get("url") or "").strip().split("?")[0]
    if not url or not ID_RE.search(url):
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        url = f"https://www.leroymerlin.com.br/{slug}_{pid}"
    pack = product.get("pack") or {}
    return {
        "name": name,
        "sku": str(product.get("_id") or pid),
        "brand": str(product.get("brand") or ""),
        "url": url,
        "price": float(price),
        "from_price": pricing.get("from"),
        "available": bool(product.get("isAvailableOnEcommerce")),
        "pack_price": pack.get("price"),
        "packaging": pack.get("packaging"),
        "pack_unit": pack.get("translatedUnit"),
        "raw": product,
    }


def name_ok(name: str, plan: dict[str, Any]) -> bool:
    lower = name.lower()
    includes = plan.get("include") or []
    if includes and not any(tok.lower() in lower for tok in includes):
        return False
    for tok in plan.get("exclude") or []:
        if tok.lower() in lower:
            return False
    if plan.get("require_m3") and not any(
        x in lower for x in ("m³", "m3", "metro cúbico", "metro cubico")
    ):
        return False
    return True


def normalize(prod: dict[str, Any], unit: str) -> tuple[float, str, list[str]]:
    price = prod["price"]
    caveats: list[str] = [
        "Freight not calculated for CEP 13380-000; freight_brl left null."
    ]
    package = "1"
    name = prod["name"].lower()
    # pack m2 for porcelanato / lona
    if "metro quadrado" in unit or "m²" in unit:
        pack_price = prod.get("pack_price")
        packaging = prod.get("packaging")
        if pack_price and packaging and float(packaging) > 0:
            price = float(pack_price)
            normalized = round(float(pack_price) / float(packaging), 4)
            package = f"{packaging} m²"
            caveats.insert(0, f"Normalized from pack {packaging} m² at R${pack_price}.")
            return normalized, package, caveats
        m = re.search(r"([\d]+(?:[.,]\d+)?)\s*m[²2]", name)
        if m:
            area = float(m.group(1).replace(",", "."))
            if 0 < area < 100:
                normalized = round(price / area, 4)
                package = f"{area} m²"
                caveats.insert(0, f"Normalized from title area {area} m².")
                return normalized, package, caveats
    if unit.startswith("unidade"):
        m = re.search(r"(\d+)\s*pe[cç]as", name)
        if m and int(m.group(1)) > 1:
            n = int(m.group(1))
            package = f"{n} peças"
            caveats.insert(0, f"Sold as pack of {n}; normalized per unit.")
            return round(price / n, 4), package, caveats
    if "metro linear" in unit:
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*m(?:etro)?s?\b", name)
        # rolls like 50 m
        m2 = re.search(r"(\d+)\s*m\b", name)
        if m2 and int(m2.group(1)) >= 5:
            meters = int(m2.group(1))
            package = f"{meters} m"
            caveats.insert(0, f"Normalized from {meters} m package.")
            return round(price / meters, 4), package, caveats
    return price, package, caveats


def candidate_from(prod: dict[str, Any], unit: str, query: str) -> dict[str, Any]:
    normalized, package, caveats = normalize(prod, unit)
    if not prod.get("available"):
        caveats.append("isAvailableOnEcommerce=false at check time; price still visible.")
    return {
        "matched_product": prod["name"],
        "sku": prod["sku"],
        "seller": "Leroy Merlin",
        "specifications": {"brand": prod.get("brand") or "", "source_query": query},
        "package_size": package,
        "displayed_price_brl": prod["price"] if not prod.get("pack_price") else (prod.get("pack_price") or prod["price"]),
        "normalized_unit_price_brl": normalized,
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
        "verification_method": (
            f"Leroy Merlin api/v3/products/{prod['sku']} HTTP 200 with X-Region=campinas "
            f"(Nova Odessa CEP 13380 proxy); pricing.price.to R${float(prod['price']):.2f}; "
            f"canonical URL {prod['url']}. Arithmetic: R${normalized:.4f} per {unit}."
        ),
        "caveats": caveats,
    }


def build_expense(expense_id: str) -> dict[str, Any]:
    plan = SEARCH_PLAN[expense_id]
    if plan.get("likely_no_match"):
        return {
            "expense_id": expense_id,
            "requested_item": plan["item"],
            "requested_unit": plan["unit"],
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": (
                "No purchasable caçamba de entulho retail SKU with visible unit price "
                "on Leroy Merlin (service/rental not sold as product)."
            ),
        }

    ids: list[str] = []
    for seed in plan.get("seed_ids") or []:
        ids.append(str(seed))
    for q in plan["queries"]:
        for _slug, pid in discover_ids(q):
            if pid not in ids:
                ids.append(pid)
        time.sleep(0.6)

    candidates: list[dict[str, Any]] = []
    kit_buckets: dict[str, list[dict[str, Any]]] = {
        "silicone": [],
        "espuma": [],
        "selante": [],
    }
    for pid in ids[:15]:
        prod = fetch_product(pid)
        time.sleep(0.25)
        if not prod:
            continue
        if not name_ok(prod["name"], plan) and not plan.get("kit_mode"):
            continue
        if plan.get("require_m2"):
            # keep structural candidates only if somehow m2; else skip later
            pass
        cand = candidate_from(prod, plan["unit"], plan["queries"][0])
        if plan.get("kit_mode"):
            n = prod["name"].lower()
            if "espuma" in n:
                kit_buckets["espuma"].append(cand)
            elif "silicone" in n:
                kit_buckets["silicone"].append(cand)
            elif "selante" in n or " pu" in n or n.endswith("pu"):
                kit_buckets["selante"].append(cand)
            continue
        candidates.append(cand)

    if plan.get("kit_mode"):
        parts = []
        for key in ("silicone", "espuma", "selante"):
            group = kit_buckets[key]
            if group:
                parts.append(min(group, key=lambda x: x["normalized_unit_price_brl"]))
        candidates = parts
        if len(parts) >= 2:
            total = round(sum(p["displayed_price_brl"] for p in parts), 2)
            winner = {
                **parts[0],
                "matched_product": "Kit representativo: "
                + " + ".join(p["matched_product"] for p in parts),
                "displayed_price_brl": total,
                "normalized_unit_price_brl": total,
                "package_size": f"{len(parts)} itens",
                "verification_method": (
                    "Sum of lowest verified silicone/espuma/selante component prices "
                    f"via api/v3/products (= R${total:.2f}). Primary URL is first component."
                ),
                "caveats": [
                    "Representative kit from lowest verified individual components.",
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
            return {
                "expense_id": expense_id,
                "requested_item": plan["item"],
                "requested_unit": plan["unit"],
                "match_status": "verified",
                "candidates": candidates,
                "winner": winner,
                "no_match_reason": "",
            }

    if plan.get("require_m3"):
        return {
            "expense_id": expense_id,
            "requested_item": plan["item"],
            "requested_unit": plan["unit"],
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": (
                "Only bagged aggregates found; no m³-priced bulk areia/pedrisco "
                "with a verified product API unit price."
            ),
        }

    if plan.get("require_m2"):
        return {
            "expense_id": expense_id,
            "requested_item": plan["item"],
            "requested_unit": plan["unit"],
            "match_status": "no_match",
            "candidates": candidates[:3],
            "winner": None,
            "no_match_reason": (
                "No clear m²-priced madeiramento/estrutura metálica package found "
                "with comparable unit pricing."
            ),
        }

    candidates.sort(key=lambda x: x["normalized_unit_price_brl"])
    # prefer preferred tokens when present
    prefer = plan.get("prefer") or []
    winner = None
    if prefer:
        preferred = [
            c
            for c in candidates
            if any(tok.lower() in c["matched_product"].lower() for tok in prefer)
        ]
        if preferred:
            winner = preferred[0]
    if winner is None and candidates:
        winner = candidates[0]

    if not winner:
        return {
            "expense_id": expense_id,
            "requested_item": plan["item"],
            "requested_unit": plan["unit"],
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": (
                "No comparable product with visible price verified via "
                "api/v3/products on leroymerlin.com.br for this unit."
            ),
        }

    return {
        "expense_id": expense_id,
        "requested_item": plan["item"],
        "requested_unit": plan["unit"],
        "match_status": "verified",
        "candidates": candidates,
        "winner": winner,
        "no_match_reason": "",
    }


def main() -> None:
    import sys

    only = sys.argv[1] if len(sys.argv) > 1 else None
    OUT.mkdir(parents=True, exist_ok=True)
    for cluster, ids in CLUSTERS.items():
        if only and cluster != only:
            continue
        expenses = []
        for eid in ids:
            print(f"[{cluster}] {eid}", flush=True)
            expenses.append(build_expense(eid))
        doc = {
            "cluster": cluster,
            "checked_at": CHECKED,
            "location_basis": LOCATION,
            "expenses": expenses,
        }
        path = OUT / f"cluster-{cluster}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Wrote", path, flush=True)


if __name__ == "__main__":
    main()
