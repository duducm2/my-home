"""Rebuild all cluster-*.json from agent API caches + live api/v3 verification."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[3]
DIR = ROOT / "data" / "research" / "leroymerlin"
CHECKED = date.today().isoformat()
LOCATION = "nova_odessa_cep_13380"
API = "https://www.leroymerlin.com.br/api/v3/products/{}"
S = requests.Session()
S.headers.update(
    {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "X-Region": "campinas",
    }
)

CLUSTERS = {
    "structural": ["EXP_0014", "EXP_0015", "EXP_0016", "EXP_0017", "EXP_0019", "EXP_0021", "EXP_0042"],
    "finishes": ["EXP_0023", "EXP_0024", "EXP_0025", "EXP_0041", "EXP_0046", "EXP_0048", "EXP_0049"],
    "openings": ["EXP_0026", "EXP_0027", "EXP_0029", "EXP_0030", "EXP_0031"],
    "plumbing": ["EXP_0028", "EXP_0036", "EXP_0037", "EXP_0039", "EXP_0040", "EXP_0044"],
    "electrical": ["EXP_0033", "EXP_0034", "EXP_0035", "EXP_0038", "EXP_0045"],
    "tools_logistics": ["EXP_0018", "EXP_0020", "EXP_0022", "EXP_0043", "EXP_0047"],
}

ITEMS = {
    "EXP_0014": ("Impermeabilizante (bianco)", "balde"),
    "EXP_0015": ("Areia grossa, fina e pedrisco", "metro cúbico (m³)"),
    "EXP_0016": ("Cimento", "saco (50 kg)"),
    "EXP_0017": ("Telha", "unidade"),
    "EXP_0019": ("Tijolinho de barro", "unidade"),
    "EXP_0021": ("Arame recozido", "quilograma (kg)"),
    "EXP_0042": ("Madeiramento ou estrutura metálica", "metro quadrado (m²)"),
    "EXP_0023": ("Porcelanato", "metro quadrado (m²)"),
    "EXP_0024": ("Rejunte de porcelanato", "quilograma (kg)"),
    "EXP_0025": ("Argamassa para o porcelanato", "saco (20 kg)"),
    "EXP_0041": ("Rodapés para acompanhar o porcelanato (R$1500)", "metro linear (m)"),
    "EXP_0046": ("Tinta", "lata (18 L)"),
    "EXP_0048": ("Silicone, espuma expansiva, selante PU", "kit"),
    "EXP_0049": ("Lona para proteção da obra", "metro quadrado (m²)"),
    "EXP_0026": ("Portas internas", "unidade"),
    "EXP_0027": ("Porta Balcão (R$2000)", "unidade"),
    "EXP_0029": ("Janela (quartos e escritório)", "unidade"),
    "EXP_0030": ("Vitrô Sala", "unidade"),
    "EXP_0031": ("Vitrôs banheiros", "unidade"),
    "EXP_0028": ("Vaso", "unidade"),
    "EXP_0036": ("Torneiras", "unidade"),
    "EXP_0037": ("Sifões e ralos", "unidade"),
    "EXP_0039": ("Pias e bancadas", "conjunto"),
    "EXP_0040": ("Box de vidro para o banheiro (R$850)", "unidade"),
    "EXP_0044": ("Caixa de água", "unidade"),
    "EXP_0033": ("Quadro de distribuição", "unidade"),
    "EXP_0034": ("Conduítes", "metro linear (m)"),
    "EXP_0035": ("Lâmpadas", "unidade"),
    "EXP_0038": ("Tomadas", "unidade"),
    "EXP_0045": ("Dispositivos de segurança", "conjunto"),
    "EXP_0018": ("Ferramentas", "conjunto"),
    "EXP_0020": ("Carrinho de mão", "unidade"),
    "EXP_0022": ("Caçamba de entulho", "caçamba"),
    "EXP_0043": ("Calhas e rufos", "metro linear (m)"),
    "EXP_0047": ("Pregos, parafusos, buchas", "pacote"),
}

NO_MATCH = {
    "EXP_0015": "Only bagged aggregates found; no m³-priced bulk areia/pedrisco on Leroy Merlin.",
    "EXP_0042": "No clear m²-priced madeiramento/estrutura metálica package verified.",
    "EXP_0022": "Caçamba de entulho is rental/service, not a retail SKU.",
    "EXP_0045": "No Leroy Merlin camera/alarm kit offer with verified unit price.",
}

# Prefer these known good IDs per expense (from agent research)
CURATED: dict[str, list[str]] = {
    "EXP_0014": ["86101561"],
    "EXP_0016": ["92137822", "89368944", "89990516", "92137836"],
    "EXP_0017": [],  # filled from cache scan
    "EXP_0019": [],
    "EXP_0021": [],
    "EXP_0023": ["92277892", "91844543", "92098860", "92334984", "92452094"],
    "EXP_0024": ["92108611", "92108380", "91931840", "90537251"],
    "EXP_0025": ["89296172", "89820234", "89684140", "87912153"],
    "EXP_0041": [],
    "EXP_0046": [],
    "EXP_0048": [],
    "EXP_0049": [],
    "EXP_0026": ["1567587108", "92026116"],
    "EXP_0027": [],
    "EXP_0029": ["1572871815", "1572483594"],
    "EXP_0030": ["1568113887"],
    "EXP_0031": [],
    "EXP_0028": ["1571666681"],
    "EXP_0036": [],
    "EXP_0037": ["1567512000"],
    "EXP_0039": [],
    "EXP_0040": [],
    "EXP_0044": ["92418711"],
    "EXP_0033": [],
    "EXP_0034": [],
    "EXP_0035": [],
    "EXP_0038": ["89676930"],
    "EXP_0018": ["1570679472", "1570679471", "89954333", "92465933"],
    "EXP_0020": ["1571958083", "1571958081", "1571958082"],
    "EXP_0043": ["1569336251", "1569336197", "1572259796"],
    "EXP_0047": [],
}


def load_finishes_cache() -> dict[str, list[dict[str, Any]]]:
    path = DIR / "_tmp_finishes_api.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_ids_from_disk() -> dict[str, list[str]]:
    """Map expense -> ids from json caches mentioning expense_id or product urls."""
    out: dict[str, list[str]] = {k: list(v) for k, v in CURATED.items()}
    # finishes cache already keyed
    finishes = load_finishes_cache()
    for eid, rows in finishes.items():
        for row in rows:
            sku = str(row.get("sku") or "")
            if sku and sku not in out.setdefault(eid, []):
                out[eid].append(sku)
    # scan all tmp json for urls + expense_id
    for path in DIR.glob("_tmp*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        blob = json.dumps(data, ensure_ascii=False)
        # expense tagged objects
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                eid = item.get("expense_id")
                url = item.get("product_url") or item.get("url") or ""
                m = re.search(r"_(\d{6,})$", str(url).split("?")[0])
                if eid and m:
                    out.setdefault(eid, [])
                    if m.group(1) not in out[eid]:
                        out[eid].append(m.group(1))
        # also harvest any ids near expense keys in finishes-like dicts
        if isinstance(data, dict):
            for k, v in data.items():
                if k.startswith("EXP_") and isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and item.get("sku"):
                            out.setdefault(k, [])
                            sku = str(item["sku"])
                            if sku not in out[k]:
                                out[k].append(sku)
    # transcript-mined structural extras from known good cement etc already set
    # keyword harvest from all ids via later API filter
    return out


def fetch(pid: str) -> dict[str, Any] | None:
    try:
        r = S.get(API.format(pid), timeout=30)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        p = r.json()["data"]["product"]
    except Exception:
        return None
    pricing = (p.get("pricing") or {}).get("price") or {}
    price = pricing.get("to")
    if price is None:
        to = (p.get("price") or {}).get("to") or {}
        if to.get("integers") is not None:
            price = float(f"{to['integers']}.{to.get('decimals') or '00'}")
    if not price or float(price) <= 0:
        return None
    url = str(p.get("url") or "").split("?")[0]
    if not url:
        slug = re.sub(r"[^a-z0-9]+", "-", str(p.get("name") or "").lower()).strip("-")
        url = f"https://www.leroymerlin.com.br/{slug}_{pid}"
    pack = p.get("pack") or {}
    return {
        "name": str(p.get("name") or "").strip(),
        "sku": str(p.get("_id") or pid),
        "brand": str(p.get("brand") or ""),
        "url": url,
        "price": float(price),
        "available": bool(p.get("isAvailableOnEcommerce")),
        "pack_price": pack.get("price"),
        "packaging": pack.get("packaging"),
        "pack_unit": pack.get("translatedUnit"),
    }


def name_matches(eid: str, name: str) -> bool:
    n = name.lower()
    rules = {
        "EXP_0014": ["bianco"],
        "EXP_0016": ["cimento"],
        "EXP_0017": ["telha"],
        "EXP_0019": ["tijolo"],
        "EXP_0021": ["arame", "recoz"],
        "EXP_0023": ["porcelanato"],
        "EXP_0024": ["rejunte"],
        "EXP_0025": ["argamassa"],
        "EXP_0041": ["rodape", "rodapé"],
        "EXP_0046": ["tinta"],
        "EXP_0048": ["silicone", "espuma", "selante"],
        "EXP_0049": ["lona"],
        "EXP_0026": ["porta"],
        "EXP_0027": ["porta", "balc"],
        "EXP_0029": ["janela"],
        "EXP_0030": ["vitro", "vitrô", "basculante"],
        "EXP_0031": ["vitro", "vitrô", "basculante"],
        "EXP_0028": ["vaso", "bacia"],
        "EXP_0036": ["torneira"],
        "EXP_0037": ["sifao", "sifão"],
        "EXP_0039": ["cuba", "pia"],
        "EXP_0040": ["box"],
        "EXP_0044": ["caixa"],
        "EXP_0033": ["quadro"],
        "EXP_0034": ["eletroduto", "conduit", "conduíte", "tubo corrug"],
        "EXP_0035": ["lampada", "lâmpada", "led"],
        "EXP_0038": ["tomada"],
        "EXP_0018": ["ferrament", "kit", "jogo", "maleta"],
        "EXP_0020": ["carrinho"],
        "EXP_0043": ["calha", "rufo", "bobina"],
        "EXP_0047": ["prego", "parafuso", "bucha"],
    }
    toks = rules.get(eid)
    if not toks:
        return True
    if eid == "EXP_0027":
        return "porta" in n and ("balc" in n or "correr" in n or "sacada" in n)
    if eid == "EXP_0021":
        return "arame" in n and "recoz" in n
    if eid == "EXP_0046":
        return "tinta" in n and "18" in n
    if eid == "EXP_0034":
        return any(t in n for t in toks)
    if eid == "EXP_0048":
        return any(t in n for t in toks)
    return any(t in n for t in toks)


def normalize(prod: dict[str, Any], unit: str) -> tuple[float, float, str, list[str]]:
    caveats = ["Freight not calculated for CEP 13380-000; freight_brl left null."]
    displayed = prod["price"]
    package = "1"
    name = prod["name"].lower()
    if ("metro quadrado" in unit or "m²" in unit) and prod.get("pack_price") and prod.get("packaging"):
        # pricing.to is often per m2; pack.price is box
        if prod.get("pack_unit") in ("m²", "m2") or True:
            # Prefer pack price / packaging when packaging is area
            try:
                area = float(prod["packaging"])
                box = float(prod["pack_price"])
                if area > 0:
                    # If price ~= box/area, displayed unit is m2
                    if abs(prod["price"] - box / area) < 1.0 or prod["price"] < box:
                        displayed = box
                        package = f"{area} m²"
                        caveats.insert(0, f"Normalized from pack {area} m² at R${box}.")
                        return displayed, round(box / area, 4), package, caveats
            except (TypeError, ValueError):
                pass
    if "metro quadrado" in unit or "m²" in unit:
        # if pricing.to is already per m2 (common for porcelanato)
        if "porcelanato" in name:
            package = f"{prod.get('packaging') or 1} m² pack unit"
            # displayed_price: prefer pack price if present else unit price
            if prod.get("pack_price"):
                displayed = float(prod["pack_price"])
                area = float(prod.get("packaging") or 1)
                return displayed, round(float(prod["price"]), 4) if abs(float(prod["price"]) - displayed / max(area, 1)) < 2 else round(displayed / area, 4), f"{area} m²", caveats
            return displayed, displayed, "m²", caveats
        m = re.search(r"(\d+)\s*[x×]\s*(\d+)\s*m", name)
        if m:
            area = int(m.group(1)) * int(m.group(2))
            return displayed, round(displayed / area, 4), f"{area} m²", [
                f"Normalized from {m.group(1)}x{m.group(2)} m sheet.",
                *caveats,
            ]
    if unit.startswith("unidade"):
        m = re.search(r"(\d+)\s*pe[cç]as", name)
        if m and int(m.group(1)) > 1:
            n = int(m.group(1))
            return displayed, round(displayed / n, 4), f"{n} peças", [
                f"Sold as pack of {n}; normalized per unit.",
                *caveats,
            ]
    if "metro linear" in unit:
        if re.search(r"x\s*2\s*m", name) or "2mts" in name or "2m" in name.replace(" ", ""):
            return displayed, round(displayed / 2, 4), "2 m", [
                "Normalized from 2 m length.",
                *caveats,
            ]
        m = re.search(r"(\d+)\s*m\b", name)
        if m and int(m.group(1)) >= 5:
            meters = int(m.group(1))
            return displayed, round(displayed / meters, 4), f"{meters} m", [
                f"Normalized from {meters} m package.",
                *caveats,
            ]
    return displayed, displayed, package, caveats


def to_cand(prod: dict[str, Any], unit: str) -> dict[str, Any]:
    displayed, normalized, package, caveats = normalize(prod, unit)
    if not prod.get("available"):
        caveats.append("isAvailableOnEcommerce=false at check time; price still visible on API.")
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
        "verification_method": (
            f"Leroy Merlin api/v3/products/{prod['sku']} HTTP 200 with X-Region=campinas "
            f"(Nova Odessa CEP 13380 proxy); pricing visible; URL {prod['url']}."
        ),
        "caveats": caveats,
    }


def build_expense(eid: str, id_map: dict[str, list[str]]) -> dict[str, Any]:
    item, unit = ITEMS[eid]
    if eid in NO_MATCH:
        return {
            "expense_id": eid,
            "requested_item": item,
            "requested_unit": unit,
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": NO_MATCH[eid],
        }

    ids = id_map.get(eid, [])
    cands: list[dict[str, Any]] = []
    kit: dict[str, list] = {"silicone": [], "espuma": [], "selante": []}

    for pid in ids[:25]:
        prod = fetch(pid)
        time.sleep(0.15)
        if not prod or not name_matches(eid, prod["name"]):
            continue
        cand = to_cand(prod, unit)
        if eid == "EXP_0048":
            n = prod["name"].lower()
            if "espuma" in n:
                kit["espuma"].append(cand)
            elif "silicone" in n:
                kit["silicone"].append(cand)
            elif "selante" in n or re.search(r"\bpu\b", n):
                kit["selante"].append(cand)
            continue
        cands.append(cand)

    if eid == "EXP_0048":
        parts = []
        for k in ("silicone", "espuma", "selante"):
            if kit[k]:
                parts.append(min(kit[k], key=lambda x: x["normalized_unit_price_brl"]))
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
                "requested_item": item,
                "requested_unit": unit,
                "match_status": "verified",
                "candidates": cands,
                "winner": winner,
                "no_match_reason": "",
            }

    cands.sort(key=lambda x: x["normalized_unit_price_brl"])
    # prefer bianco 18L
    if eid == "EXP_0014":
        pref = [c for c in cands if "18" in c["matched_product"]]
        if pref:
            cands = pref + [c for c in cands if c not in pref]

    if not cands:
        return {
            "expense_id": eid,
            "requested_item": item,
            "requested_unit": unit,
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": "No comparable product with visible price verified via api/v3/products.",
        }

    return {
        "expense_id": eid,
        "requested_item": item,
        "requested_unit": unit,
        "match_status": "verified",
        "candidates": cands,
        "winner": cands[0],
        "no_match_reason": "",
    }


def main() -> None:
    id_map = collect_ids_from_disk()
    # Extra: harvest ALL skus from finishes cache into keyword pools for empty expenses
    # Also pull ids from tools_price_parse / openings
    for path_name in [
        "_tmp_tools_price_parse.json",
        "_tmp_jina_prices.json",
        "_tmp_openings_bing.json",
        "_tmp_brave_plumbing.json",
        "_tmp_brave_electrical.json",
        "_tmp_exp0033_offers.json",
    ]:
        path = DIR / path_name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"_(\d{6,})", text):
            # will filter by name later — stash under a global pool
            id_map.setdefault("_POOL", [])
            if m.group(1) not in id_map["_POOL"]:
                id_map["_POOL"].append(m.group(1))

    # For expenses with few ids, add pool (filtered by name_matches)
    pool = id_map.pop("_POOL", [])
    for eid in ITEMS:
        if eid in NO_MATCH:
            continue
        if len(id_map.get(eid, [])) < 3:
            id_map.setdefault(eid, [])
            for pid in pool:
                if pid not in id_map[eid]:
                    id_map[eid].append(pid)

    for cluster, eids in CLUSTERS.items():
        expenses = []
        for eid in eids:
            print(f"[{cluster}] {eid} ids={len(id_map.get(eid, []))}", flush=True)
            expenses.append(build_expense(eid, id_map))
        path = DIR / f"cluster-{cluster}.json"
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
