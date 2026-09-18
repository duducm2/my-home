"""Discover PU sealant IDs and fetch a few extras."""
from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()
queries = [
    "selante poliuretano 400g leroymerlin.com.br",
    "selante pu branco leroymerlin.com.br",
    "selante pu 380ml leroymerlin",
]
cdn_re = re.compile(
    r"cdn\.leroymerlin\.com\.br/products/([a-z0-9_,.\-]+?)_(\d{6,})_",
    re.I,
)
found: list[str] = []
for q in queries:
    url = "https://www.bing.com/images/search?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=35, context=ctx) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        print("ERR", q, e)
        continue
    for m in cdn_re.finditer(html):
        path = m.group(1).replace("_", "-") + "_" + m.group(2)
        if path not in found:
            found.append(path)
print("found", len(found))
for p in found[:40]:
    print(p)

# fetch top matching IDs via API
ids = []
for p in found:
    if re.search(r"selante|poliuret|pu-", p, re.I) and not re.search(
        r"espuma|silicone", p, re.I
    ):
        mid = re.search(r"_(\d+)$", p)
        if mid:
            ids.append(int(mid.group(1)))

print("api ids", ids[:20])


def fetch(pid: int):
    url = f"https://www.leroymerlin.com.br/api/v3/products/{pid}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "X-Region": "campinas",
        },
    )
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        raw = r.read().decode("utf-8", "replace").strip()
    if not raw:
        return {"sku": pid, "error": "empty"}
    data = json.loads(raw)
    p = data["data"]["product"]
    price = (p.get("pricing") or {}).get("price") or {}
    return {
        "sku": pid,
        "name": p.get("name"),
        "price": price.get("to"),
        "avail": p.get("isAvailableOnEcommerce"),
        "url": p.get("url"),
    }


for pid in ids[:15]:
    try:
        print(fetch(pid))
    except Exception as e:
        print(pid, e)
