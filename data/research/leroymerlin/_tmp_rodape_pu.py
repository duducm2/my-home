"""Discover rodapé and PU sealant URLs via Bing web results + API probe."""
from __future__ import annotations

import base64
import json
import re
import ssl
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()


def bing_links(q: str) -> list[str]:
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(q) + "&count=30"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=35, context=ctx) as r:
        html = r.read().decode("utf-8", "replace")
    out: list[str] = []
    for m in re.finditer(
        r"https://www\.leroymerlin\.com\.br/([a-z0-9,\-]+_\d+)", html, re.I
    ):
        u = "https://www.leroymerlin.com.br/" + m.group(1)
        if u not in out:
            out.append(u)
    for m in re.finditer(r"u=a1(aHR0c[A-Za-z0-9+/=]+)", html):
        b = m.group(1)
        pad = "=" * ((4 - len(b) % 4) % 4)
        try:
            dec = base64.b64decode(b + pad).decode("utf-8", "replace")
        except Exception:
            continue
        if "leroymerlin.com.br/" in dec:
            u = dec.split("?")[0]
            if re.search(r"_\d+$", u) and u not in out:
                out.append(u)
    for m in re.finditer(
        r"cdn\.leroymerlin\.com\.br/products/([a-z0-9_,.\-]+?)_(\d{6,})_",
        html,
        re.I,
    ):
        u = (
            "https://www.leroymerlin.com.br/"
            + m.group(1).replace("_", "-")
            + "_"
            + m.group(2)
        )
        if u not in out:
            out.append(u)
    return out


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
            return None
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
        return {"sku": pid, "error": str(e)}


queries = [
    "rodape poliestireno 7cm site:leroymerlin.com.br",
    "rodape branco 2,40 site:leroymerlin.com.br",
    "rodape mdf 7cm leroymerlin.com.br",
    "selante pu40 site:leroymerlin.com.br",
    "selante poliuretano branco leroymerlin.com.br",
    "selante pu construção leroymerlin",
    "sika flex pu leroymerlin.com.br",
]

all_urls: list[str] = []
for q in queries:
    try:
        links = bing_links(q)
        print("===", q, "n=", len(links))
        for u in links[:20]:
            print(" ", u)
            if u not in all_urls:
                all_urls.append(u)
    except Exception as e:
        print("ERR", q, e)

# fetch product details for discovered URLs
print("\nFETCH discovered")
for u in all_urls:
    m = re.search(r"_(\d+)$", u)
    if not m:
        continue
    pid = int(m.group(1))
    d = api(pid)
    if not d:
        continue
    name = (d.get("name") or d.get("error") or "")[:90]
    print(pid, d.get("price"), d.get("avail"), name)

# also probe bing shop for rodape
print("\nSHOP probe via search titles already have IDs above")
