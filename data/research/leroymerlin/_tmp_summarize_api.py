"""Summarize finishes API results."""
from __future__ import annotations

import json
from pathlib import Path

d = json.loads(
    Path(
        r"C:\Users\eduev\Meu Drive\17 - Projects\my-home\data\research\leroymerlin\_tmp_finishes_api.json"
    ).read_text(encoding="utf-8")
)
for exp, items in d.items():
    print("==", exp, "n=", len(items))
    priced = [
        x
        for x in items
        if x.get("displayed_price_brl") and x.get("is_available_ecommerce")
    ]
    priced.sort(key=lambda x: x["displayed_price_brl"])
    for x in priced[:10]:
        name = (x.get("matched_product") or "")[:75]
        print(
            f"  {x['displayed_price_brl']:8.2f} {x.get('sku')} "
            f"unit={x.get('unit')} pack={x.get('packaging')} {name}"
        )
    if not priced:
        anyp = [x for x in items if x.get("displayed_price_brl")]
        anyp.sort(key=lambda x: x["displayed_price_brl"])
        print("  (no available) showing priced anyway:")
        for x in anyp[:6]:
            name = (x.get("matched_product") or "")[:75]
            print(
                f"  {x['displayed_price_brl']:8.2f} {x.get('sku')} "
                f"avail={x.get('is_available_ecommerce')} {name}"
            )
