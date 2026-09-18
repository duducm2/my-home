"""Probe more rodapé / rejunte branco / selante PU product IDs."""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()


def api(pid: int):
    url = f"https://www.leroymerlin.com.br/api/v3/products/{pid}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "X-Region": "campinas",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            raw = r.read().decode("utf-8", "replace").strip()
        if not raw:
            return {"sku": pid, "error": "empty"}
        p = json.loads(raw)["data"]["product"]
        price = (p.get("pricing") or {}).get("price") or {}
        return {
            "sku": pid,
            "name": p.get("name"),
            "price": price.get("to"),
            "avail": p.get("isAvailableOnEcommerce"),
            "url": p.get("url"),
            "unit": p.get("unit"),
            "pack": p.get("pack"),
            "chars": {
                c.get("name"): c.get("value")
                for c in (p.get("characteristics") or [])
            },
        }
    except Exception as e:
        return {"sku": pid, "error": f"{type(e).__name__}: {e}"}


# IDs from earlier image titles + nearby Axton rejunte IDs + common PU sealants
ids = [
    # rejunte branco guesses near known Axton IDs
    92108373,
    92108366,
    92108604,
    92108618,
    92108387,
    90537244,
    90537237,
    90537268,
    91931833,
    91931847,
    # rodapé guesses / related
    1571598281,
    1572343516,
    1571598274,
    1571598298,
    88401200,
    90350000,
    # selante PU common marketplace IDs sometimes shared
    88654321,
    89123456,
]
# Also scrape bing shop HTML for rodape
shop_q = [
    "rodape poliestireno leroymerlin",
    "rodape 7cm branco leroymerlin",
    "selante pu leroymerlin",
    "selante poliuretano leroymerlin",
]
cdn_re = re.compile(
    r"cdn\.leroymerlin\.com\.br/products/([a-z0-9_,.\-]+?)_(\d{6,})_", re.I
)
url_re = re.compile(r"leroymerlin\.com\.br/([a-z0-9,\-]+_\d+)", re.I)
for q in shop_q:
    url = "https://www.bing.com/shop?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=35, context=ctx) as r:
            html = r.read().decode("utf-8", "replace")
        print("SHOP", q, "len", len(html))
        found = []
        for m in cdn_re.finditer(html):
            path = m.group(1).replace("_", "-") + "_" + m.group(2)
            if path not in found:
                found.append(path)
        for m in url_re.finditer(html):
            path = m.group(1)
            if path not in found:
                found.append(path)
        for p in found[:20]:
            print(" ", p)
            mid = re.search(r"_(\d+)$", p)
            if mid:
                ids.append(int(mid.group(1)))
    except Exception as e:
        print("SHOP ERR", q, e)

# unique
seen = set()
uniq_ids = []
for i in ids:
    if i not in seen:
        seen.add(i)
        uniq_ids.append(i)

print("probing", len(uniq_ids), "ids")
hits = []
for pid in uniq_ids:
    d = api(pid)
    name = (d.get("name") or d.get("error") or "")[:90]
    print(pid, d.get("price"), d.get("avail"), name)
    if d.get("price") and d.get("avail") and d.get("name"):
        hits.append(d)
    time.sleep(0.15)

print("\nHITS", len(hits))
for h in hits:
    print(h["sku"], h["price"], h["name"][:80])
