"""Search public indexes for Leroy Merlin electrical product URLs/prices."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from html import unescape

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

QUERIES = [
    "site:leroymerlin.com.br quadro de distribuicao",
    "site:leroymerlin.com.br quadro distribuicao embutir",
    "site:leroymerlin.com.br eletroduto corrugado",
    "site:leroymerlin.com.br eletroduto corrugado 25mm",
    "site:leroymerlin.com.br lampada led bulbo 9w",
    "site:leroymerlin.com.br lâmpada led e27",
    "site:leroymerlin.com.br tomada 2P+T 10A",
    "site:leroymerlin.com.br tomada plug 10a",
    "site:leroymerlin.com.br kit camera seguranca",
    "site:leroymerlin.com.br kit alarme residencial",
]

PRODUCT_RE = re.compile(
    r"https?://(?:www\.)?leroymerlin\.com\.br/[a-z0-9\-]+_\d+",
    re.I,
)
PRICE_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=35) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def bing(q: str) -> str:
    return fetch("https://www.bing.com/search?q=" + urllib.parse.quote(q) + "&setlang=pt-br&cc=BR")


def ddg(q: str) -> str:
    return fetch("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))


def extract(html: str, source: str, query: str) -> list[dict]:
    out = []
    for m in PRODUCT_RE.finditer(html):
        url = m.group(0).replace("http://", "https://")
        if not url.startswith("https://www."):
            url = url.replace("https://leroymerlin.com.br", "https://www.leroymerlin.com.br")
        # local context for price/title
        start = max(0, m.start() - 400)
        end = min(len(html), m.end() + 400)
        ctx = unescape(re.sub(r"<[^>]+>", " ", html[start:end]))
        ctx = re.sub(r"\s+", " ", ctx).strip()
        prices = PRICE_RE.findall(ctx)
        out.append(
            {
                "source": source,
                "query": query,
                "url": url.rstrip("/"),
                "context": ctx[:350],
                "prices_in_context": prices[:3],
            }
        )
    # dedupe by url keeping first
    seen = set()
    deduped = []
    for item in out:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        deduped.append(item)
    return deduped


def main() -> None:
    results: list[dict] = []
    for q in QUERIES:
        for name, fn in (("bing", bing), ("ddg", ddg)):
            try:
                html = fn(q)
                items = extract(html, name, q)
                print(f"[{name}] {q}: {len(items)} urls")
                for it in items[:8]:
                    print(" ", it["url"], it["prices_in_context"], it["context"][:120])
                results.extend(items)
            except Exception as exc:
                print(f"ERR {name} {q}: {exc}")
    path = __file__.replace("_tmp_search_electrical.py", "_tmp_search_electrical_out.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Wrote", path, "total", len(results))


if __name__ == "__main__":
    main()
