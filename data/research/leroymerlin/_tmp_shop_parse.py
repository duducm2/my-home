"""Parse Bing shop HTML for LM product IDs (rodapé / selante)."""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()


def fetch_shop(q: str) -> str:
    url = "https://www.bing.com/shop?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
        return r.read().decode("utf-8", "replace")


def extract_ids(html: str) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    patterns = [
        r"cdn\.leroymerlin\.com\.br/products/([a-z0-9_,.\-]+?)_(\d{6,})_",
        r"leroymerlin\.com\.br/([a-z0-9,\-]+)_(\d{6,})",
        r"products%2f([a-z0-9_]+?)_(\d{6,})_",
        r"products\\\\?/([a-z0-9_]+?)_(\d{6,})_",
    ]
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, html, re.I):
            slug, pid = m.group(1), int(m.group(2))
            key = (slug.lower(), pid)
            if key in seen:
                continue
            seen.add(key)
            found.append((slug.replace("_", "-"), pid))
    return found


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
    except Exception:
        return None


for q in [
    "rodape poliestireno leroymerlin",
    "rodape 7cm branco leroymerlin",
    "selante pu leroymerlin",
    "selante poliuretano leroymerlin",
    "pu40 quartzolit leroymerlin",
]:
    html = fetch_shop(q)
    items = extract_ids(html)
    print("===", q, "ids", len(items), "html", len(html))
    # show interesting
    interesting = [
        x
        for x in items
        if re.search(r"rodap|selante|poliuret|pu40|pu-40|flex", x[0], re.I)
    ]
    show = interesting or items[:15]
    for slug, pid in show[:25]:
        print(" ", pid, slug[:80])
        d = api(pid)
        if d and d.get("name"):
            print(
                "   ->",
                d.get("price"),
                d.get("avail"),
                (d.get("name") or "")[:80],
            )
        time.sleep(0.12)
