"""Bing Shopping lookups for Leroy Merlin openings products."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PRODUCT_RE = re.compile(
    r"https?://(?:www\.)?leroymerlin\.com\.br/([a-z0-9%,._-]+_\d+)",
    re.I,
)

QUERIES = {
    "EXP_0026": [
        "folha de porta madeira lisa 210x80 site:leroymerlin.com.br",
        "folha de porta madeira lisa 210x80cm melaminica mgm leroymerlin",
        "folha de porta 210x80 leroymerlin.com.br",
    ],
    "EXP_0027": [
        "porta balcao aluminio correr site:leroymerlin.com.br",
        "porta de correr aluminio sacada leroymerlin",
        "porta balcao 4 folhas aluminio leroymerlin",
    ],
    "EXP_0029": [
        "janela de correr 4 folhas 120x120 site:leroymerlin.com.br",
        "janela classic 120x120 leroymerlin",
        "janela de correr aluminio branco 04 folhas leroymerlin",
    ],
    "EXP_0030": [
        "vitro basculante 60x60 site:leroymerlin.com.br",
        "vitrô basculante 60x60 leroymerlin",
        "vitro basculante aluminio 60x60 hale leroymerlin",
    ],
    "EXP_0031": [
        "vitro basculante 40x40 site:leroymerlin.com.br",
        "vitro basculante 50x50 leroymerlin",
        "vitro basculante 60x40 leroymerlin",
    ],
}


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def clean_url(url: str) -> str:
    return url.split("?")[0].rstrip("/")


def parse_query(q: str) -> dict:
    url = "https://www.bing.com/shop?" + urllib.parse.urlencode(
        {"q": q, "setlang": "pt-br"}
    )
    html = fetch(url)
    urls: list[str] = []
    offers: list[dict] = []
    for m in PRODUCT_RE.finditer(html):
        product_url = clean_url(m.group(0))
        urls.append(product_url)
        start = max(0, m.start() - 2000)
        end = min(len(html), m.end() + 1200)
        chunk = html[start:end]
        prices = re.findall(r"R\$\s*([\d.]+,\d{2})", chunk)
        titles = re.findall(
            r"(?:title|aria-label)=\"([^\"]{12,180})\"", chunk, re.I
        )
        offers.append(
            {
                "url": product_url,
                "sku": m.group(1).rsplit("_", 1)[-1],
                "prices_nearby": prices[:6],
                "titles_nearby": titles[:4],
                "has_leroy": bool(re.search(r"leroy", chunk, re.I)),
            }
        )
    for mm in re.finditer(
        r"\"url\"\s*:\s*\"(https:\\/\\/www\.leroymerlin\.com\.br\\/[^\"]+)\"",
        html,
    ):
        u = mm.group(1).encode().decode("unicode_escape").replace("\\/", "/")
        urls.append(clean_url(u))
    # Extract offer cards mentioning Leroy Merlin with price + title
    cards = []
    for m in re.finditer(r"Leroy Merlin", html, re.I):
        start = max(0, m.start() - 2500)
        end = min(len(html), m.end() + 800)
        chunk = html[start:end]
        prices = re.findall(r"R\$\s*([\d.]+,\d{2})", chunk)
        titles = re.findall(
            r"(?:title|aria-label)=\"([^\"]{12,180})\"", chunk, re.I
        )
        prod = PRODUCT_RE.findall(chunk)
        cards.append(
            {
                "prices": prices[:6],
                "titles": titles[:5],
                "lm_slugs": prod[:5],
            }
        )
    return {
        "query": q,
        "html_len": len(html),
        "lm_urls": list(dict.fromkeys(urls))[:40],
        "offers": offers[:40],
        "leroy_cards": cards[:25],
        "sample_prices": re.findall(r"R\$\s*[\d.]+,\d{2}", html)[:25],
    }


def main() -> None:
    out: dict = {}
    for eid, qs in QUERIES.items():
        rows = []
        for q in qs:
            try:
                rows.append(parse_query(q))
            except Exception as exc:  # noqa: BLE001
                rows.append({"query": q, "error": str(exc)})
        out[eid] = rows
    path = Path(__file__).with_name("_tmp_openings_bing.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path} bytes={path.stat().st_size}")


if __name__ == "__main__":
    main()
