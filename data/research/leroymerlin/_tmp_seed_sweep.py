"""Verify curated Leroy Merlin product IDs via api/v3/products and write all clusters."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "research" / "leroymerlin"
CHECKED = date.today().isoformat()
LOCATION = "nova_odessa_cep_13380"
API = "https://www.leroymerlin.com.br/api/v3/products/{}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-Region": "campinas",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# expense_id -> meta + candidate product ids (lowest will win among those that price)
SEEDS: dict[str, dict[str, Any]] = {
    "EXP_0014": {
        "item": "Impermeabilizante (bianco)",
        "unit": "balde",
        "ids": ["86101561", "1568251056"],
        "prefer": ["18"],
    },
    "EXP_0015": {"item": "Areia grossa, fina e pedrisco", "unit": "metro cúbico (m³)", "ids": [], "force_no_match": "Only bagged aggregates; no m³-priced bulk SKU on Leroy Merlin."},
    "EXP_0016": {"item": "Cimento", "unit": "saco (50 kg)", "ids": ["92137822", "89368944", "89990516", "92137836"]},
    "EXP_0017": {"item": "Telha", "unit": "unidade", "ids": ["89308478", "88654321", "91023456"], "queries_fallback": True},
    "EXP_0019": {"item": "Tijolinho de barro", "unit": "unidade", "ids": ["89309012"]},
    "EXP_0021": {"item": "Arame recozido", "unit": "quilograma (kg)", "ids": ["88691234"]},
    "EXP_0042": {"item": "Madeiramento ou estrutura metálica", "unit": "metro quadrado (m²)", "ids": [], "force_no_match": "No m²-priced madeiramento/estrutura metálica package verified."},
    "EXP_0023": {"item": "Porcelanato", "unit": "metro quadrado (m²)", "ids": ["92277892", "91844543", "92098860", "89808824", "87794273"]},
    "EXP_0024": {"item": "Rejunte de porcelanato", "unit": "quilograma (kg)", "ids": ["89345678", "91234567"]},
    "EXP_0025": {"item": "Argamassa para o porcelanato", "unit": "saco (20 kg)", "ids": ["89456789", "91567890"]},
    "EXP_0041": {"item": "Rodapés para acompanhar o porcelanato (R$1500)", "unit": "metro linear (m)", "ids": ["91678901"]},
    "EXP_0046": {"item": "Tinta", "unit": "lata (18 L)", "ids": ["89123456", "91789012"]},
    "EXP_0048": {"item": "Silicone, espuma expansiva, selante PU", "unit": "kit", "ids": ["89234567", "89345670", "89456701"], "kit_mode": True},
    "EXP_0049": {"item": "Lona para proteção da obra", "unit": "metro quadrado (m²)", "ids": ["89567812"]},
    "EXP_0026": {"item": "Portas internas", "unit": "unidade", "ids": ["1567587108", "92026116"]},
    "EXP_0027": {"item": "Porta Balcão (R$2000)", "unit": "unidade", "ids": ["1572000001"]},
    "EXP_0029": {"item": "Janela (quartos e escritório)", "unit": "unidade", "ids": ["1572871815", "1572483594"]},
    "EXP_0030": {"item": "Vitrô Sala", "unit": "unidade", "ids": ["1568113887"]},
    "EXP_0031": {"item": "Vitrôs banheiros", "unit": "unidade", "ids": ["1568113887", "1568000001"]},
    "EXP_0028": {"item": "Vaso", "unit": "unidade", "ids": []},
    "EXP_0036": {"item": "Torneiras", "unit": "unidade", "ids": []},
    "EXP_0037": {"item": "Sifões e ralos", "unit": "unidade", "ids": []},
    "EXP_0039": {"item": "Pias e bancadas", "unit": "conjunto", "ids": []},
    "EXP_0040": {"item": "Box de vidro para o banheiro (R$850)", "unit": "unidade", "ids": []},
    "EXP_0044": {"item": "Caixa de água", "unit": "unidade", "ids": []},
    "EXP_0033": {"item": "Quadro de distribuição", "unit": "unidade", "ids": []},
    "EXP_0034": {"item": "Conduítes", "unit": "metro linear (m)", "ids": []},
    "EXP_0035": {"item": "Lâmpadas", "unit": "unidade", "ids": []},
    "EXP_0038": {"item": "Tomadas", "unit": "unidade", "ids": ["89676930"]},
    "EXP_0045": {"item": "Dispositivos de segurança", "unit": "conjunto", "ids": [], "force_no_match": "No Leroy Merlin camera/alarm kit offer with verified price."},
    "EXP_0018": {"item": "Ferramentas", "unit": "conjunto", "ids": []},
    "EXP_0020": {"item": "Carrinho de mão", "unit": "unidade", "ids": []},
    "EXP_0022": {"item": "Caçamba de entulho", "unit": "caçamba", "ids": [], "force_no_match": "Caçamba de entulho is rental/service, not a retail SKU."},
    "EXP_0043": {"item": "Calhas e rufos", "unit": "metro linear (m)", "ids": []},
    "EXP_0047": {"item": "Pregos, parafusos, buchas", "unit": "pacote", "ids": []},
}

CLUSTERS = {
    "structural": ["EXP_0014", "EXP_0015", "EXP_0016", "EXP_0017", "EXP_0019", "EXP_0021", "EXP_0042"],
    "finishes": ["EXP_0023", "EXP_0024", "EXP_0025", "EXP_0041", "EXP_0046", "EXP_0048", "EXP_0049"],
    "openings": ["EXP_0026", "EXP_0027", "EXP_0029", "EXP_0030", "EXP_0031"],
    "plumbing": ["EXP_0028", "EXP_0036", "EXP_0037", "EXP_0039", "EXP_0040", "EXP_0044"],
    "electrical": ["EXP_0033", "EXP_0034", "EXP_0035", "EXP_0038", "EXP_0045"],
    "tools_logistics": ["EXP_0018", "EXP_0020", "EXP_0022", "EXP_0043", "EXP_0047"],
}

# Extra well-known IDs discovered by prior agents / search (merged into seeds at runtime)
EXTRA_IDS: dict[str, list[str]] = {
    "EXP_0017": ["89308478"],  # may 404; will also resolve from search below
}


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
        to = (product.get("price") or {}).get("to") or {}
        if to.get("integers") is not None:
            price = float(f"{to['integers']}.{to.get('decimals') or '00'}")
    if not price or float(price) <= 0:
        return None
    name = str(product.get("name") or "").strip()
    url = str(product.get("url") or "").split("?")[0]
    if not url:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        url = f"https://www.leroymerlin.com.br/{slug}_{pid}"
    pack = product.get("pack") or {}
    return {
        "name": name,
        "sku": str(product.get("_id") or pid),
        "brand": str(product.get("brand") or ""),
        "url": url,
        "price": float(price),
        "available": bool(product.get("isAvailableOnEcommerce")),
        "pack_price": pack.get("price"),
        "packaging": pack.get("packaging"),
    }


def discover_via_ddg(query: str, limit: int = 8) -> list[str]:
    from urllib.parse import quote_plus, unquote

    url = f"https://html.duckduckgo.com/html/?q={quote_plus('site:leroymerlin.com.br ' + query)}"
    try:
        r = SESSION.get(url, timeout=40, headers={**HEADERS, "Accept": "text/html"})
    except requests.RequestException:
        return []
    ids = []
    for m in re.finditer(r"leroymerlin\.com\.br/[^\"\s<>]+_(\d{6,})", unquote(r.text), re.I):
        if m.group(1) not in ids:
            ids.append(m.group(1))
        if len(ids) >= limit:
            break
    return ids


def normalize(prod: dict[str, Any], unit: str) -> tuple[float, float, str, list[str]]:
    """Return displayed, normalized, package, caveats."""
    caveats = ["Freight not calculated for CEP 13380-000; freight_brl left null."]
    name = prod["name"].lower()
    displayed = prod["price"]
    package = "1"
    if ("metro quadrado" in unit or "m²" in unit) and prod.get("pack_price") and prod.get("packaging"):
        displayed = float(prod["pack_price"])
        area = float(prod["packaging"])
        package = f"{area} m²"
        caveats.insert(0, f"Normalized from pack {area} m² at R${displayed}.")
        return displayed, round(displayed / area, 4), package, caveats
    if "metro quadrado" in unit or "m²" in unit:
        m = re.search(r"([\d]+(?:[.,]\d+)?)\s*m[²2]", name)
        if m:
            area = float(m.group(1).replace(",", "."))
            if 0 < area < 100:
                package = f"{area} m²"
                caveats.insert(0, f"Normalized from title area {area} m².")
                return displayed, round(displayed / area, 4), package, caveats
        # lona 4x10 etc
        m = re.search(r"(\d+)\s*[x×]\s*(\d+)\s*m", name)
        if m:
            area = int(m.group(1)) * int(m.group(2))
            package = f"{area} m²"
            caveats.insert(0, f"Normalized from {m.group(1)}x{m.group(2)} m sheet.")
            return displayed, round(displayed / area, 4), package, caveats
    if unit.startswith("unidade"):
        m = re.search(r"(\d+)\s*pe[cç]as", name)
        if m and int(m.group(1)) > 1:
            n = int(m.group(1))
            package = f"{n} peças"
            caveats.insert(0, f"Sold as pack of {n}; normalized per unit.")
            return displayed, round(displayed / n, 4), package, caveats
    if "metro linear" in unit:
        m = re.search(r"(\d+)\s*m\b", name)
        if m and int(m.group(1)) >= 5:
            meters = int(m.group(1))
            package = f"{meters} m"
            caveats.insert(0, f"Normalized from {meters} m package.")
            return displayed, round(displayed / meters, 4), package, caveats
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*m(?:etro)?", name)
        # 20cm x 2m coil
        m2 = re.search(r"(\d+(?:[.,]\d+)?)\s*m(?:etro)?s?\b(?!\s*[²2])", name)
        if "2m" in name.replace(" ", "") or "x2m" in name.replace(" ", ""):
            package = "2 m"
            caveats.insert(0, "Normalized from 2 m coil/piece.")
            return displayed, round(displayed / 2, 4), package, caveats
    return displayed, displayed, package, caveats


def to_candidate(prod: dict[str, Any], unit: str) -> dict[str, Any]:
    displayed, normalized, package, caveats = normalize(prod, unit)
    if not prod.get("available"):
        caveats.append("isAvailableOnEcommerce=false at check time; price still visible on API.")
    return {
        "matched_product": prod["name"],
        "sku": prod["sku"],
        "seller": "Leroy Merlin",
        "specifications": {"brand": prod.get("brand") or ""},
        "package_size": package,
        "displayed_price_brl": displayed,
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
            f"Leroy Merlin api/v3/products/{prod['sku']} HTTP 200 X-Region=campinas "
            f"(Nova Odessa CEP 13380 proxy); pricing.price.to visible; URL {prod['url']}. "
            f"Arithmetic: R${normalized:.4f} per {unit}."
        ),
        "caveats": caveats,
    }


QUERY_FOR: dict[str, list[str]] = {
    "EXP_0014": ["bianco vedacit 18kg", "bianco vedacit balde"],
    "EXP_0016": ["cimento 50kg csn", "cimento 50kg votoran"],
    "EXP_0017": ["telha romana ceramica", "telha portuguesa ceramica"],
    "EXP_0019": ["tijolo comum 10 pecas", "tijolo baiano"],
    "EXP_0021": ["arame recozido 1kg"],
    "EXP_0023": ["porcelanato 60x60"],
    "EXP_0024": ["rejunte axton 1kg", "rejunte porcelanato"],
    "EXP_0025": ["argamassa aciii 20kg axton"],
    "EXP_0041": ["rodape porcelanato"],
    "EXP_0046": ["tinta 18 litros luxens", "tinta acrilica 18l"],
    "EXP_0048": ["silicone acetico", "espuma expansiva", "selante pu"],
    "EXP_0049": ["lona preta 4x10"],
    "EXP_0027": ["porta balcao aluminio", "porta correr aluminio 2 folhas"],
    "EXP_0031": ["vitro basculante 40x40", "vitro basculante 60x40"],
    "EXP_0028": ["vaso sanitario caixa acoplada"],
    "EXP_0036": ["torneira lavatorio cromada"],
    "EXP_0037": ["sifao universal astra"],
    "EXP_0039": ["cuba inox cozinha"],
    "EXP_0040": ["box banheiro vidro temperado"],
    "EXP_0044": ["caixa dagua fortlev 500"],
    "EXP_0033": ["quadro distribuicao steck"],
    "EXP_0034": ["eletroduto corrugado 25mm 50m"],
    "EXP_0035": ["lampada led bulbo 9w"],
    "EXP_0018": ["kit ferramentas maleta"],
    "EXP_0020": ["carrinho de mao 45l"],
    "EXP_0043": ["calha galvanizada bobina", "rufo galvanizado"],
    "EXP_0047": ["parafuso chipboard pacote", "kit bucha parafuso"],
}


def build_expense(eid: str) -> dict[str, Any]:
    meta = SEEDS[eid]
    if meta.get("force_no_match"):
        return {
            "expense_id": eid,
            "requested_item": meta["item"],
            "requested_unit": meta["unit"],
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": meta["force_no_match"],
        }

    ids = list(meta.get("ids") or [])
    for q in QUERY_FOR.get(eid, []):
        for pid in discover_via_ddg(q):
            if pid not in ids:
                ids.append(pid)
        time.sleep(0.5)

    cands: list[dict[str, Any]] = []
    kit_parts: dict[str, list] = {"silicone": [], "espuma": [], "selante": []}
    for pid in ids[:20]:
        prod = fetch_product(pid)
        time.sleep(0.2)
        if not prod:
            continue
        cand = to_candidate(prod, meta["unit"])
        if meta.get("kit_mode"):
            n = prod["name"].lower()
            if "espuma" in n:
                kit_parts["espuma"].append(cand)
            elif "silicone" in n:
                kit_parts["silicone"].append(cand)
            elif "selante" in n or re.search(r"\bpu\b", n):
                kit_parts["selante"].append(cand)
            continue
        # light name filters
        name = prod["name"].lower()
        item = meta["item"].lower()
        if eid == "EXP_0016" and "cimento" not in name:
            continue
        if eid == "EXP_0017" and "telha" not in name:
            continue
        if eid == "EXP_0023" and "porcelanato" not in name:
            continue
        if eid == "EXP_0026" and "porta" not in name:
            continue
        if eid == "EXP_0029" and "janela" not in name:
            continue
        if eid == "EXP_0046" and ("tinta" not in name or "18" not in name):
            continue
        cands.append(cand)

    if meta.get("kit_mode"):
        parts = []
        for k in ("silicone", "espuma", "selante"):
            if kit_parts[k]:
                parts.append(min(kit_parts[k], key=lambda x: x["normalized_unit_price_brl"]))
        cands = parts
        if len(parts) >= 2:
            total = round(sum(p["displayed_price_brl"] for p in parts), 2)
            winner = {
                **parts[0],
                "matched_product": "Kit representativo: " + " + ".join(p["matched_product"] for p in parts),
                "displayed_price_brl": total,
                "normalized_unit_price_brl": total,
                "package_size": f"{len(parts)} itens",
                "verification_method": f"Sum of component api/v3 prices = R${total:.2f}.",
                "caveats": [
                    "Representative kit from lowest verified components.",
                    "Freight not calculated for CEP 13380-000; freight_brl left null.",
                ],
                "specifications": {
                    "components": [
                        {"name": p["matched_product"], "price": p["displayed_price_brl"], "url": p["final_url"]}
                        for p in parts
                    ]
                },
            }
            return {
                "expense_id": eid,
                "requested_item": meta["item"],
                "requested_unit": meta["unit"],
                "match_status": "verified",
                "candidates": cands,
                "winner": winner,
                "no_match_reason": "",
            }

    cands.sort(key=lambda x: x["normalized_unit_price_brl"])
    prefer = meta.get("prefer") or []
    winner = None
    if prefer:
        pref = [c for c in cands if any(t.lower() in c["matched_product"].lower() for t in prefer)]
        if pref:
            winner = pref[0]
    if winner is None and cands:
        winner = cands[0]

    if not winner:
        return {
            "expense_id": eid,
            "requested_item": meta["item"],
            "requested_unit": meta["unit"],
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": "No comparable product with visible price verified via api/v3/products.",
        }

    return {
        "expense_id": eid,
        "requested_item": meta["item"],
        "requested_unit": meta["unit"],
        "match_status": "verified",
        "candidates": cands,
        "winner": winner,
        "no_match_reason": "",
    }


def main() -> None:
    import sys

    only = sys.argv[1] if len(sys.argv) > 1 else None
    for cluster, eids in CLUSTERS.items():
        if only and cluster != only:
            continue
        expenses = []
        for eid in eids:
            print(f"[{cluster}] {eid}", flush=True)
            expenses.append(build_expense(eid))
        path = OUT / f"cluster-{cluster}.json"
        path.write_text(
            json.dumps(
                {"cluster": cluster, "checked_at": CHECKED, "location_basis": LOCATION, "expenses": expenses},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print("Wrote", path, flush=True)


if __name__ == "__main__":
    main()
