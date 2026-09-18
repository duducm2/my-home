"""Bing HTML search for Leroy Merlin product URLs."""
from __future__ import annotations

import re
import ssl
import urllib.parse
import urllib.request

queries = [
    "porcelanato 60x60 site:leroymerlin.com.br",
    "rejunte acrilico 1kg site:leroymerlin.com.br",
    "argamassa ACIII 20kg site:leroymerlin.com.br",
    "rodape porcelanato site:leroymerlin.com.br",
    "tinta acrilica 18L site:leroymerlin.com.br",
    "silicone acetico site:leroymerlin.com.br",
    "espuma expansiva site:leroymerlin.com.br",
    "selante PU site:leroymerlin.com.br",
    "lona plastica site:leroymerlin.com.br",
]

ctx = ssl.create_default_context()
product_re = re.compile(r"https://www\.leroymerlin\.com\.br/[a-zA-Z0-9,\-._%]+_\d+")
href_re = re.compile(r'href="(https://www\.leroymerlin\.com\.br[^"]+)"')

for q in queries:
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(q) + "&count=30"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    print("===", q)
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            html = r.read().decode("utf-8", "replace")
        links = product_re.findall(html)
        # also cite links like /ck/a?...
        cite = re.findall(r'cite[^>]*>([^<]*leroymerlin[^<]*)', html, re.I)
        raw_hrefs = href_re.findall(html)
        uniq = list(dict.fromkeys(links))
        print(" products", len(uniq))
        for u in uniq[:12]:
            print(" ", u)
        if not uniq:
            print(" cites", cite[:8])
            lm_hrefs = [h for h in raw_hrefs if "leroymerlin" in h][:10]
            for h in lm_hrefs:
                print("  href", h[:180])
            # dump snippet around first leroymerlin
            idx = html.lower().find("leroymerlin.com.br/")
            if idx >= 0:
                print("  snip", html[idx : idx + 220].replace("\n", " "))
    except Exception as e:
        print(" ERR", type(e).__name__, e)
