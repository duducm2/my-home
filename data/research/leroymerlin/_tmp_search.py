"""Search-engine lookups for Leroy Merlin product snippets (no direct LM scrape)."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PRODUCT_RE = re.compile(r"https?://(?:www\.)?leroymerlin\.com\.br/[a-z0-9,\-]+_\d+", re.I)
PRICE_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")

QUERIES = [
    "site:leroymerlin.com.br Bianco Vedacit 18kg",
    "site:leroymerlin.com.br aditivo chapisco bianco 18",
    "site:leroymerlin.com.br cimento 50kg votoran",
    "site:leroymerlin.com.br cimento cp ii 50kg",
    "site:leroymerlin.com.br telha ceramica romana",
    "site:leroymerlin.com.br telha ceramica portuguesa",
    "site:leroymerlin.com.br tijolo comum",
    "site:leroymerlin.com.br tijolinho barro",
    "site:leroymerlin.com.br arame recozido 1kg",
    "site:leroymerlin.com.br areia saco 20kg",
    "site:leroymerlin.com.br estrutura metalica telhado",
    "site:leroymerlin.com.br areia metro cubico",
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def search_ddg(q: str) -> dict:
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q})
    html = fetch(url)
    urls = list(dict.fromkeys(PRODUCT_RE.findall(html)))
    prices = PRICE_RE.findall(html)
    # also pull uddg redirect targets
    for m in re.finditer(r"uddg=([^&\"']+)", html):
        decoded = urllib.parse.unquote(m.group(1))
        urls.extend(PRODUCT_RE.findall(decoded))
    urls = list(dict.fromkeys(urls))
    return {"query": q, "urls": urls[:20], "prices": prices[:20], "html_len": len(html)}


def search_bing(q: str) -> dict:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": q, "setlang": "pt-BR"})
    html = fetch(url)
    urls = list(dict.fromkeys(PRODUCT_RE.findall(html)))
    prices = PRICE_RE.findall(html)
    # bing often encodes as /ck/a?... 
    for m in re.finditer(r"https?://www\.leroymerlin\.com\.br/[a-z0-9,\-]+_\d+", html, re.I):
        urls.append(m.group(0))
    urls = list(dict.fromkeys(urls))
    # extract snippet-ish lines near product urls
    snippets = []
    for u in urls[:10]:
        idx = html.lower().find(u.lower())
        if idx >= 0:
            snippets.append(re.sub(r"\s+", " ", html[max(0, idx - 80) : idx + len(u) + 200])[:280])
    return {"query": q, "urls": urls[:20], "prices": prices[:20], "snippets": snippets[:10], "html_len": len(html)}


def main() -> None:
    out = {"ddg": [], "bing": []}
    for q in QUERIES:
        try:
            out["ddg"].append(search_ddg(q))
        except Exception as e:
            out["ddg"].append({"query": q, "error": str(e)})
        try:
            out["bing"].append(search_bing(q))
        except Exception as e:
            out["bing"].append({"query": q, "error": str(e)})
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
