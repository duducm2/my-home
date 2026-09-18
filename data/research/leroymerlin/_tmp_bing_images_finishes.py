"""Discover LM product IDs from Bing image CDN URLs for remaining finishes expenses."""
from __future__ import annotations

import re
import ssl
import urllib.parse
import urllib.request
from html import unescape

queries = [
    "porcelanato 60x60 caixa site:cdn.leroymerlin.com.br",
    "porcelanato 60x60 leroymerlin.com.br",
    "rodape porcelanato leroymerlin.com.br",
    "rodape mdf 7cm leroymerlin.com.br",
    "tinta acrilica 18L branco leroymerlin.com.br",
    "tinta acrilica fosco 18 litros coral leroymerlin",
    "silicone acetico 280ml leroymerlin.com.br",
    "espuma expansiva 500ml leroymerlin.com.br",
    "selante PU 400g leroymerlin.com.br",
    "lona plastica preta m2 leroymerlin.com.br",
    "lona reforçada 100 micras leroymerlin.com.br",
]

ctx = ssl.create_default_context()
cdn_re = re.compile(
    r"cdn\.leroymerlin\.com\.br/products/([a-z0-9_]+?)_(\d{5,})_([a-z0-9]+)_",
    re.I,
)
product_url_re = re.compile(
    r"https://www\.leroymerlin\.com\.br/([a-z0-9,\-]+_\d+)",
    re.I,
)

for q in queries:
    url = "https://www.bing.com/images/search?q=" + urllib.parse.quote(q) + "&qft=+filterui:license-L2_L3_L4&form=IRFLTR"
    # simpler images search
    url = "https://www.bing.com/images/search?q=" + urllib.parse.quote(q) + "&first=1"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    print("===", q)
    try:
        with urllib.request.urlopen(req, timeout=35, context=ctx) as r:
            html = r.read().decode("utf-8", "replace")
        found = []
        for m in cdn_re.finditer(html):
            slug_u, pid, _hash = m.group(1), m.group(2), m.group(3)
            slug = slug_u.replace("_", "-")
            # CDN slug often includes the id already at end - check
            # pattern was products/<name>_<id>_<hash>
            # but name may already end before id
            path = f"{slug}_{pid}" if not slug.endswith(pid) else slug
            # Fix: slug_u is name without id; path = name-with-hyphens_id
            path = f"{slug_u.replace('_', '-')}_{pid}"
            if path not in found:
                found.append(path)
        for m in product_url_re.finditer(html):
            p = m.group(1)
            if p not in found:
                found.append(p)
        # also murl encoded
        for m in re.finditer(r"murl&quot;:&quot;([^&]+?cdn\.leroymerlin[^&]+)", html):
            u = unescape(m.group(1))
            for cm in cdn_re.finditer(u):
                path = f"{cm.group(1).replace('_', '-')}_{cm.group(2)}"
                if path not in found:
                    found.append(path)
        print(" found", len(found))
        for p in found[:15]:
            print(" ", p)
    except Exception as e:
        print(" ERR", type(e).__name__, e)
