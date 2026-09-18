"""Fetch Leroy Merlin finishes cluster prices via api/v3/products with X-Region campinas."""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

ctx = ssl.create_default_context()
OUT = Path(
    r"C:\Users\eduev\Meu Drive\17 - Projects\my-home\data\research\leroymerlin\_tmp_finishes_api.json"
)
CHECKED = "2026-09-17"
LOC = "nova_odessa_cep_13380"
REGION = "campinas"  # regional proxy for Nova Odessa/SP CEP 13380

# expense -> list of product IDs (numeric) discovered via Bing CDN / redirects
PRODUCTS: dict[str, list[int]] = {
    "EXP_0023": [
        92334984,
        92452094,
        92334991,
        92399202,
        92270612,
        92089326,
        89373326,
        87890516,
        92270633,
        92270626,
        92103893,
        87935162,
        92390606,
        90983683,
        89374320,
        89566162,
        92098860,
        91844543,
        89555851,
        1572186910,
        92277892,
        92298192,
        92338610,
        89540710,
        92492064,
        89562711,
        91074760,
        89555830,
    ],
    "EXP_0024": [
        91931840,
        91931875,
        92367394,
        92380953,
        1570939729,
        92108380,
        92108611,
        90537251,
        1571039551,
        1571980463,
        1571039535,
    ],
    "EXP_0025": [
        89296172,
        87125962,
        87912153,
        89684140,
        92524775,
        90985930,
        92394743,
        89229791,
        92322503,
        92173144,
        90609092,
        89820234,
        92453333,
        90609106,
        90220144,
        85526182,
        86857680,
        92394750,
        92394736,
    ],
    "EXP_0041": [
        1572343516,
        1571598281,
    ],
    "EXP_0046": [
        92334816,
        91934913,
        1570463379,
        92136492,
        91917105,
        1567429733,
        1572427654,
        1571327766,
        91934703,
        1569838395,
        91917560,
        92386434,
        1569838373,
        92259160,
        1570686744,
        90707596,
        92098503,
        91918134,
        1567018586,
        91917014,
        89330444,
        1572396533,
        92499316,
        89669636,
        91939484,
        1569838362,
        92175384,
        1571918152,
        1570715574,
    ],
    "EXP_0048_silicone": [
        1571505158,
        1568648235,
        1571928010,
        1572130176,
        1572104620,
        1571612621,
        88363443,
        89302773,
        1566819730,
        91039466,
        1567475755,
        1571505159,
        1570761256,
        1566805967,
        92216103,
        89945261,
        88363205,
        1566819734,
    ],
    "EXP_0048_espuma": [
        1568116649,
        1572364358,
        1571504289,
        91039634,
        1570547930,
        1567953934,
        1571919695,
        1571024549,
        1571893762,
        92216033,
        1572690047,
        1569818046,
        89796392,
        1571486897,
        91869953,
        1571504230,
        87257156,
        1568249521,
    ],
    "EXP_0048_selante_pu": [
        # will discover; try common
    ],
    "EXP_0049": [
        89186713,
        92349376,
        90910575,
        92339023,
        1571796615,
        90910540,
        88036865,
        1571965958,
        88514104,
        1569931951,
        1572465915,
        90910561,
        1566851737,
        1571835450,
        91980763,
        92069551,
        88514160,
        88514125,
        92450225,
        1568122153,
        1568122196,
        1566851672,
    ],
}


def fetch_product(pid: int) -> dict:
    url = f"https://www.leroymerlin.com.br/api/v3/products/{pid}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "X-Region": REGION,
            "Referer": "https://www.leroymerlin.com.br/",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=35, context=ctx) as r:
            status = r.status
            raw = r.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        return {"sku": str(pid), "http_status": e.code, "error": body}
    except Exception as e:
        return {"sku": str(pid), "http_status": 0, "error": f"{type(e).__name__}: {e}"}
    if not raw:
        return {"sku": str(pid), "http_status": status, "error": "empty body"}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "sku": str(pid),
            "http_status": status,
            "error": "non-json",
            "sample": raw[:200],
        }
    product = (payload.get("data") or {}).get("product") or {}
    if not product:
        return {
            "sku": str(pid),
            "http_status": status,
            "error": "no product",
            "raw_keys": list(payload.keys()),
        }

    pricing = product.get("pricing") or {}
    price_obj = pricing.get("price") or {}
    to_price = price_obj.get("to")
    from_price = price_obj.get("from")
    # fallback nested integers/decimals
    if to_price is None:
        p = product.get("price") or {}
        to_n = p.get("to") or {}
        if isinstance(to_n, dict) and to_n.get("integers") is not None:
            to_price = float(f"{to_n['integers']}.{to_n.get('decimals') or '00'}")
        elif isinstance(to_n, (int, float)):
            to_price = float(to_n)

    chars = {
        c.get("name"): c.get("value")
        for c in (product.get("characteristics") or [])
        if isinstance(c, dict) and c.get("name")
    }
    pack = product.get("pack") or {}
    packaging = product.get("packaging") or {}

    return {
        "sku": str(product.get("_id") or pid),
        "http_status": status,
        "matched_product": product.get("name"),
        "brand": product.get("brand"),
        "product_url": product.get("url"),
        "unit": product.get("unit"),
        "packaging_unit": product.get("packagingUnit"),
        "pack": pack,
        "packaging": packaging,
        "displayed_price_brl": to_price,
        "from_price_brl": from_price,
        "is_available_ecommerce": product.get("isAvailableOnEcommerce"),
        "characteristics": chars,
        "discount_pct": (pricing.get("discount") or {}).get("percentage"),
        "region": REGION,
    }


results: dict[str, list] = {}
for exp, pids in PRODUCTS.items():
    results[exp] = []
    print(f"== {exp} ({len(pids)} ids) ==")
    for pid in pids:
        print(f"  fetch {pid}", flush=True)
        data = fetch_product(pid)
        data["expense_id"] = exp
        results[exp].append(data)
        print(
            "   ->",
            data.get("http_status"),
            data.get("displayed_price_brl"),
            (data.get("matched_product") or data.get("error") or "")[:70],
            "avail",
            data.get("is_available_ecommerce"),
            flush=True,
        )
        time.sleep(0.25)

OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("Wrote", OUT)
