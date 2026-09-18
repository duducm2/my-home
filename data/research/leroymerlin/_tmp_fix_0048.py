import json
import time
from datetime import date
from pathlib import Path

import requests

DIR = Path(__file__).resolve().parent
CHECKED = date.today().isoformat()
LOCATION = "nova_odessa_cep_13380"
S = requests.Session()
S.headers.update(
    {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "X-Region": "campinas"}
)


def fetch(pid: str):
    r = S.get(f"https://www.leroymerlin.com.br/api/v3/products/{pid}", timeout=30)
    if r.status_code != 200:
        return None
    p = r.json()["data"]["product"]
    price = ((p.get("pricing") or {}).get("price") or {}).get("to")
    if not price:
        return None
    return {
        "name": p["name"],
        "sku": str(p["_id"]),
        "brand": p.get("brand") or "",
        "url": p.get("url"),
        "price": float(price),
        "available": bool(p.get("isAvailableOnEcommerce")),
    }


def cand(p, unit):
    return {
        "matched_product": p["name"],
        "sku": p["sku"],
        "seller": "Leroy Merlin",
        "specifications": {"brand": p["brand"]},
        "package_size": "1",
        "displayed_price_brl": p["price"],
        "normalized_unit_price_brl": p["price"],
        "unit": unit,
        "minimum_quantity": 1,
        "bulk_tiers": [],
        "freight_brl": None,
        "availability": "in_stock" if p["available"] else "limited",
        "location_basis": LOCATION,
        "checked_at": CHECKED,
        "product_url": p["url"],
        "final_url": p["url"],
        "http_status": 200,
        "verification_method": f"api/v3/products/{p['sku']} HTTP 200 X-Region=campinas",
        "caveats": ["Freight not calculated for CEP 13380-000; freight_brl left null."],
    }


sil = fetch("1572130176")
time.sleep(0.1)
esp = fetch("1571024549")
assert sil and esp
parts = [cand(sil, "kit"), cand(esp, "kit")]
total = round(sum(x["displayed_price_brl"] for x in parts), 2)
winner = {
    **parts[0],
    "matched_product": "Kit representativo: "
    + " + ".join(p["matched_product"] for p in parts),
    "displayed_price_brl": total,
    "normalized_unit_price_brl": total,
    "package_size": "2 itens (silicone + espuma; PU nao verificado)",
    "verification_method": f"Sum silicone+espuma api prices R${total:.2f}",
    "caveats": [
        "Representative kit; selante PU not verified.",
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
path = DIR / "cluster-finishes.json"
doc = json.loads(path.read_text(encoding="utf-8"))
for i, e in enumerate(doc["expenses"]):
    if e["expense_id"] == "EXP_0048":
        doc["expenses"][i] = {
            "expense_id": "EXP_0048",
            "requested_item": "Silicone, espuma expansiva, selante PU",
            "requested_unit": "kit",
            "match_status": "verified",
            "candidates": parts,
            "winner": winner,
            "no_match_reason": "",
        }
doc["checked_at"] = CHECKED
path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("EXP_0048", total)
