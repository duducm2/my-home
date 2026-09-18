"""Deeper search: Google/Bing HTML + DDG raw for prices near product URLs."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
PRODUCT_RE = re.compile(r"https?://(?:www\.)?leroymerlin\.com\.br/[a-z0-9,\.\-]+_\d+", re.I)
PRICE_RE = re.compile(r"R\$\s*[\d.]+,\d{2}")

QUERIES = [
    "site:leroymerlin.com.br Bianco Vedacit 18kg",
    "site:leroymerlin.com.br cimento 50kg",
    "site:leroymerlin.com.br cimento votoran 50kg",
    "site:leroymerlin.com.br telha ceramica romana",
    "site:leroymerlin.com.br telha ceramica portuguesa",
    "site:leroymerlin.com.br tijolo comum",
    "site:leroymerlin.com.br arame recozido 1kg",
    "site:leroymerlin.com.br areia 20kg",
    "site:leroymerlin.com.br pedrisco 20kg",
    "site:leroymerlin.com.br caibro eucalipto",
    '"aditivo-para-chapisco-vedacit-bianco-18kg" preço',
    '"cimento-cp-ii-f-32-todas-as-obras-50kg-votoran" preço',
    '"arame-recozido-trancado-1kg-arcelormittal" preço',
    '"telha-de-ceramica-romana" leroymerlin preço',
]


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_context(html: str) -> list[dict]:
    out = []
    for m in PRODUCT_RE.finditer(html):
        start = max(0, m.start() - 250)
        end = min(len(html), m.end() + 350)
        chunk = re.sub(r"<[^>]+>", " ", html[start:end])
        chunk = re.sub(r"\s+", " ", chunk).strip()
        prices = PRICE_RE.findall(chunk)
        out.append({"url": m.group(0), "prices_nearby": prices, "context": chunk[:400]})
    # dedupe by url keep first with prices
    seen = {}
    for item in out:
        u = item["url"].split("?")[0].rstrip("/")
        if u not in seen or (item["prices_nearby"] and not seen[u]["prices_nearby"]):
            seen[u] = item
            seen[u]["url"] = u
    return list(seen.values())


def search_google(q: str) -> dict:
    url = "https://www.google.com/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "pt-BR", "num": "10"}
    )
    html = fetch(url)
    blocked = "unusual traffic" in html.lower() or "captcha" in html.lower()
    return {
        "engine": "google",
        "query": q,
        "blocked": blocked,
        "html_len": len(html),
        "items": extract_context(html),
        "all_prices": PRICE_RE.findall(html)[:30],
        "title_hint": re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S),
    }


def search_ddg(q: str) -> dict:
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q})
    html = fetch(url)
    # expand uddg
    expanded = html
    for m in re.finditer(r"uddg=([^&\"']+)", html):
        expanded += "\n" + urllib.parse.unquote(m.group(1))
    return {
        "engine": "ddg",
        "query": q,
        "html_len": len(html),
        "items": extract_context(expanded),
        "all_prices": PRICE_RE.findall(html)[:30],
    }


def search_bing(q: str) -> dict:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": q, "setlang": "pt-br"})
    html = fetch(url)
    # Bing often uses encoded urls; also look for slug_id without domain
    items = extract_context(html)
    # find slug_id patterns
    for m in re.finditer(r"([a-z0-9,\.\-]{8,}_\d{5,})", html, re.I):
        slug = m.group(1)
        if "leroymerlin" in html[max(0, m.start() - 200) : m.end() + 50].lower() or True:
            u = f"https://www.leroymerlin.com.br/{slug}"
            start = max(0, m.start() - 250)
            end = min(len(html), m.end() + 350)
            chunk = re.sub(r"<[^>]+>", " ", html[start:end])
            chunk = re.sub(r"\s+", " ", chunk).strip()
            prices = PRICE_RE.findall(chunk)
            if prices or "leroymerlin" in chunk.lower():
                items.append({"url": u, "prices_nearby": prices, "context": chunk[:400]})
    return {
        "engine": "bing",
        "query": q,
        "html_len": len(html),
        "items": items[:25],
        "all_prices": PRICE_RE.findall(html)[:30],
        "has_leroymerlin_text": "leroymerlin" in html.lower(),
    }


def main() -> None:
    results = []
    for q in QUERIES:
        for fn in (search_ddg, search_google, search_bing):
            try:
                r = fn(q)
                if "title_hint" in r and r["title_hint"]:
                    r["title"] = re.sub(r"\s+", " ", r["title_hint"].group(1)).strip()
                    del r["title_hint"]
                elif "title_hint" in r:
                    del r["title_hint"]
                # keep only useful
                if r.get("items") or r.get("all_prices") or r.get("blocked"):
                    results.append(r)
            except Exception as e:
                results.append({"engine": fn.__name__, "query": q, "error": str(e)})
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
