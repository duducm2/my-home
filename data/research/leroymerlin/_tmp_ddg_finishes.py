"""DuckDuckGo HTML search for Leroy Merlin product URLs (finishes cluster)."""
from __future__ import annotations

import re
import ssl
import urllib.parse
import urllib.request
from urllib.parse import unquote

queries = [
    "site:leroymerlin.com.br porcelanato 60x60",
    "site:leroymerlin.com.br porcelanato 60x60 caixa m2",
    "site:leroymerlin.com.br rejunte acrilico 1kg",
    "site:leroymerlin.com.br rejunte porcelanato quartzolit",
    "site:leroymerlin.com.br argamassa ACIII 20kg",
    "site:leroymerlin.com.br argamassa porcelanato 20kg",
    "site:leroymerlin.com.br rodape porcelanato",
    "site:leroymerlin.com.br rodape 7cm mdf",
    "site:leroymerlin.com.br tinta acrilica 18L branco",
    "site:leroymerlin.com.br tinta 18 litros",
    "site:leroymerlin.com.br silicone acetico 280ml",
    "site:leroymerlin.com.br espuma expansiva PU",
    "site:leroymerlin.com.br selante PU 400g",
    "site:leroymerlin.com.br lona plastica preta",
    "site:leroymerlin.com.br lona protecao obra",
]

ctx = ssl.create_default_context()
product_re = re.compile(r"https://www\.leroymerlin\.com\.br/[a-zA-Z0-9,\-._%]+_\d+")

for q in queries:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    print("===", q)
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            html = r.read().decode("utf-8", "replace")
        enc = re.findall(r"uddg=([^&\"]+)", html)
        links: list[str] = []
        for e in enc:
            u = unquote(e).split("&")[0]
            if "leroymerlin.com.br" in u:
                links.append(u.split("?")[0])
        links += product_re.findall(html)
        uniq: list[str] = []
        for u in links:
            if u not in uniq and re.search(r"_\d+$", u):
                uniq.append(u)
        if not uniq:
            # category/search pages
            any_lm = []
            for e in enc:
                u = unquote(e).split("&")[0]
                if "leroymerlin.com.br" in u and u not in any_lm:
                    any_lm.append(u)
            for u in any_lm[:8]:
                print("  raw", u[:160])
        else:
            for u in uniq[:15]:
                print(" ", u)
    except Exception as e:
        print("  ERR", type(e).__name__, e)
