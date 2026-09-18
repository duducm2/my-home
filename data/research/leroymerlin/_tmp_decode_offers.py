"""Extract Bing Shopping LM offers (price + decoded product URL) via saved HTML or stdin JSON."""
from __future__ import annotations

import base64
import json
import re
import urllib.parse
from pathlib import Path

PRICE_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")
PROD_RE = re.compile(
    r"https?://(?:www\.)?leroymerlin\.com\.br/[a-z0-9\-]+_\d+", re.I
)


def decode_u(u: str) -> str:
    text = urllib.parse.unquote(u)
    if "%" in text:
        text = urllib.parse.unquote(text)
    # base64 form used in aclick
    if text.startswith("aHR0"):
        pad = "=" * (-len(text) % 4)
        try:
            text = base64.b64decode(text + pad).decode("utf-8", errors="ignore")
            text = urllib.parse.unquote(text)
        except Exception:
            pass
    return text


def from_href(href: str) -> str:
    m = re.search(r"[?&]u=([^&]+)", href)
    if not m:
        if PROD_RE.search(href):
            return PROD_RE.search(href).group(0).split("?")[0]
        return ""
    url = decode_u(m.group(1))
    m2 = PROD_RE.search(url)
    return m2.group(0).split("?")[0] if m2 else url.split("?")[0]


def parse_price(text: str) -> float | None:
    m = PRICE_RE.search(text.replace("\xa0", " "))
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def extract_from_cdp_offers(offers: list[dict]) -> list[dict]:
    out = []
    for o in offers:
        text = o.get("text") or ""
        if "Leroy Merlin" not in text and "leroymerlin" not in (o.get("href") or "").lower():
            # still keep if href decodes to LM
            pass
        url = from_href(o.get("href") or "")
        if "leroymerlin.com.br" not in url:
            continue
        if not re.search(r"_\d+$", url.rstrip("/")):
            continue
        price = parse_price(text)
        if price is None:
            continue
        title = re.sub(r"\s*R\$.*", "", text).replace("Leroy Merlin", "").strip(" ….")
        out.append(
            {
                "matched_product": title[:180],
                "displayed_price_brl": price,
                "product_url": url.rstrip("/"),
                "raw_text": text[:220],
            }
        )
    # dedupe by url keep lowest price
    best: dict[str, dict] = {}
    for item in out:
        u = item["product_url"]
        if u not in best or item["displayed_price_brl"] < best[u]["displayed_price_brl"]:
            best[u] = item
    return sorted(best.values(), key=lambda x: x["displayed_price_brl"])


def main() -> None:
    src = Path(
        r"C:\Users\eduev\.cursor\browser-logs\cdp-response-Runtime.evaluate-2026-09-18T01-00-57-588Z.json"
    )
    data = json.loads(src.read_text(encoding="utf-8"))
    offers = data["result"]["value"]["offers"]
    items = extract_from_cdp_offers(offers)
    out = Path(__file__).with_name("_tmp_exp0033_decoded.json")
    out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    for it in items[:15]:
        print(f"{it['displayed_price_brl']:8.2f}  {it['matched_product'][:70]}")
        print(f"         {it['product_url']}")


if __name__ == "__main__":
    main()
