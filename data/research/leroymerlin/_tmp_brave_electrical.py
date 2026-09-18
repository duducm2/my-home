"""Brave Search for Leroy Merlin electrical SKUs."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
OUT = Path(__file__).with_name("_tmp_brave_electrical.json")

QUERIES = {
    "EXP_0033": [
        "leroymerlin quadro de distribuicao embutir",
        "leroymerlin quadro distribuicao 12 disjuntores",
        "site:www.leroymerlin.com.br quadro distribuição",
    ],
    "EXP_0034": [
        "leroymerlin eletroduto corrugado 25mm",
        "leroymerlin eletroduto flexivel corrugado rolo",
        "leroymerlin conduíte corrugado",
    ],
    "EXP_0035": [
        "leroymerlin lampada led bulbo 9w",
        "leroymerlin lâmpada led e27 bulbo",
        "leroymerlin lampada led 9w",
    ],
    "EXP_0038": [
        "leroymerlin tomada 2P+T 10A",
        "leroymerlin tomada plug 10a",
        "leroymerlin tomada 2p+t branca",
    ],
    "EXP_0045": [
        "leroymerlin kit camera seguranca",
        "leroymerlin kit alarme residencial",
        "leroymerlin kit cftv camera",
    ],
}

PROD_RE = re.compile(r"(?:https?://(?:www\.)?)?leroymerlin\.com\.br/([a-z0-9\-]+_\d+)", re.I)
PRICE_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")


def normalize(url_or_path: str) -> str:
    m = PROD_RE.search(url_or_path)
    if not m:
        return ""
    return "https://www.leroymerlin.com.br/" + m.group(1)


def fetch_brave(q: str) -> str:
    url = "https://search.brave.com/search?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract(html: str, query: str) -> list[dict]:
    items = []
    seen = set()
    for m in PROD_RE.finditer(html):
        url = normalize(m.group(0))
        if not url or url in seen:
            continue
        seen.add(url)
        start = max(0, m.start() - 500)
        end = min(len(html), m.end() + 500)
        ctx = re.sub(r"<[^>]+>", " ", html[start:end])
        ctx = re.sub(r"\s+", " ", ctx).strip()
        prices = PRICE_RE.findall(ctx)
        items.append(
            {
                "url": url,
                "query": query,
                "slug": url.rsplit("/", 1)[-1],
                "prices_nearby": prices[:4],
                "context": ctx[:400],
            }
        )
    return items


def main() -> None:
    catalog: dict[str, list[dict]] = {}
    for expense_id, queries in QUERIES.items():
        collected: list[dict] = []
        seen = set()
        for q in queries:
            try:
                html = fetch_brave(q)
            except Exception as exc:
                print("ERR", expense_id, q, exc)
                time.sleep(2)
                continue
            print(expense_id, q, "bytes", len(html), "hits", len(PROD_RE.findall(html)))
            for item in extract(html, q):
                if item["url"] in seen:
                    continue
                seen.add(item["url"])
                collected.append(item)
                print(" ", item["url"], item["prices_nearby"])
            time.sleep(1.5)
        catalog[expense_id] = collected
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
