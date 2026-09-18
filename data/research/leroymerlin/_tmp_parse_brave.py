"""Parse cached Brave Search HTML → product URL + price pairs."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

TEMP = Path(os.environ["TEMP"])
OUT = Path(__file__).resolve().parent / "_tmp_brave_plumbing.json"

# Allow HTML tags between Price: and R$
PRICE_NEAR = re.compile(
    r"Price:</strong>\s*<span[^>]*>R\$\s*([\d,]+\.?\d*)",
    re.I,
)
PRICE_FLEX = re.compile(
    r"Price:(?:<[^>]+>|\s)*R\$\s*([\d,]+\.?\d*)",
    re.I,
)
PRODUCT_HREF = re.compile(
    r'href="(https://www\.leroymerlin\.com\.br/[^"]+_\d+)"'
)
PRODUCT_ANY = re.compile(
    r"https://www\.leroymerlin\.com\.br/[a-zA-Z0-9\-_%\.,]+_\d+"
)


def parse_price(raw: str) -> float:
    return float(raw.replace(",", ""))


def clean_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse(html: str) -> list[dict]:
    items: list[dict] = []

    # Strategy: for each Price match, walk backward to nearest product URL
    for pm in PRICE_FLEX.finditer(html):
        price = parse_price(pm.group(1))
        before = html[max(0, pm.start() - 4000) : pm.start()]
        ums = list(PRODUCT_ANY.finditer(before))
        if not ums:
            continue
        url = ums[-1].group(0).split("?")[0]
        # title: look for full_title or heading near url
        title = None
        window = html[max(0, ums[-1].start() - 200) : pm.end() + 50]
        tm = re.search(
            r'full_title:"((?:\\\\.|[^"\\\\])*)"', window
        )
        if tm:
            try:
                title = (
                    tm.group(1)
                    .encode("utf-8")
                    .decode("unicode_escape")
                    .replace(" | Leroy Merlin", "")
                )
            except Exception:
                title = tm.group(1).replace(" | Leroy Merlin", "")
        if not title:
            # anchor text in result card
            am = re.search(
                rf'href="{re.escape(url)}"[^>]*>(.*?)</a>',
                before[-2000:] + html[pm.start() : pm.end()],
                re.S,
            )
            if am:
                title = clean_text(am.group(1))
        items.append(
            {"url": url, "title": title, "price": price, "source": "price-back"}
        )

    # Also collect titles from result cards even without price
    for um in PRODUCT_HREF.finditer(html):
        url = um.group(1).split("?")[0]
        after = html[um.end() : um.end() + 500]
        title = None
        # Often title is in a sibling link; scan surrounding block
        block_start = html.rfind('class="result-content', 0, um.start())
        block = html[block_start : block_start + 6000] if block_start != -1 else ""
        if block:
            tm = re.search(
                r'class="[^"]*title[^"]*"[^>]*>(.*?)</a>', block, re.S | re.I
            )
            if tm:
                title = clean_text(tm.group(1)).replace(" | Leroy Merlin", "")
            pm = PRICE_FLEX.search(block)
            price = parse_price(pm.group(1)) if pm else None
        else:
            price = None
        items.append(
            {
                "url": url,
                "title": title,
                "price": price,
                "source": "href-card",
            }
        )

    # JSON blobs with full_title
    for m in re.finditer(
        r'url:"(https://www\.leroymerlin\.com\.br/[^"]+_\d+)".{0,600}?'
        r'full_title:"((?:\\\\.|[^"\\\\])*)"',
        html,
        re.S,
    ):
        title = m.group(2)
        try:
            title = title.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass
        title = title.replace(" | Leroy Merlin", "")
        region = html[max(0, m.start() - 500) : m.end() + 2000]
        pm = PRICE_FLEX.search(region)
        items.append(
            {
                "url": m.group(1),
                "title": title,
                "price": parse_price(pm.group(1)) if pm else None,
                "source": "json",
            }
        )

    by: dict[str, dict] = {}
    for it in items:
        # skip category/filter URLs that still match somehow
        if "/tipo-de-material/" in it["url"] or it["url"].count("/") > 3:
            # product pages are host + /slug_id — one path segment
            path = it["url"].split("leroymerlin.com.br/", 1)[-1]
            if "/" in path.rstrip("/"):
                continue
        u = it["url"]
        cur = by.get(u)
        if cur is None:
            by[u] = it
            continue
        merged = {
            "url": u,
            "title": it.get("title") or cur.get("title"),
            "price": it.get("price") if it.get("price") is not None else cur.get("price"),
            "source": it["source"] + "+" + cur["source"],
        }
        # Prefer lower price if both have prices? No — keep first priced; they should match
        if cur.get("price") and it.get("price") and cur["price"] != it["price"]:
            # keep the one from price-back as more reliable pairing
            if "price-back" in it["source"]:
                merged["price"] = it["price"]
            else:
                merged["price"] = cur["price"]
        by[u] = merged
    return list(by.values())


def fetch(query: str, out: Path) -> Path:
    url = "https://search.brave.com/search?q=" + urllib.parse.quote(query)
    subprocess.run(
        [
            "curl.exe",
            "-sL",
            "-A",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            url,
            "-o",
            str(out),
        ],
        check=True,
    )
    return out


def main() -> None:
    files = {
        "vaso": TEMP / "brave_vaso.html",
        "torneira": TEMP / "brave_torneira.html",
        "sifao": TEMP / "brave_sifao.html",
        "cuba": TEMP / "brave_cuba.html",
        "box": TEMP / "brave_box.html",
        "caixa": TEMP / "brave_caixa.html",
    }

    # Extra queries for thin categories
    extras = [
        ("sifao", "sifao blukit OR tigre site:leroymerlin.com.br", TEMP / "brave_sifao_b.html"),
        ("sifao", "sifao sanfonado site:leroymerlin.com.br", TEMP / "brave_sifao_c.html"),
        ("caixa", "caixa dagua 1000 litros site:leroymerlin.com.br", TEMP / "brave_caixa_1000.html"),
        ("caixa", "caixa dagua 750 litros fortlev site:leroymerlin.com.br", TEMP / "brave_caixa_750.html"),
        ("vaso", "kit bacia caixa acoplada site:leroymerlin.com.br", TEMP / "brave_vaso_b.html"),
        ("box", "box temperado banheiro speed site:leroymerlin.com.br", TEMP / "brave_box_b.html"),
    ]

    all_results: dict[str, list] = {k: [] for k in files}
    for key, path in files.items():
        if path.exists() and path.stat().st_size > 100000:
            all_results[key].extend(parse(path.read_text(encoding="utf-8", errors="ignore")))

    for key, query, path in extras:
        time.sleep(2.5)
        fetch(query, path)
        size = path.stat().st_size
        print(f"fetched {path.name} size={size}")
        if size > 100000:
            all_results[key].extend(
                parse(path.read_text(encoding="utf-8", errors="ignore"))
            )

    # Dedup per category
    final: dict[str, list] = {}
    for key, items in all_results.items():
        by: dict[str, dict] = {}
        for it in items:
            u = it["url"]
            cur = by.get(u)
            if cur is None:
                by[u] = it
            else:
                by[u] = {
                    "url": u,
                    "title": it.get("title") or cur.get("title"),
                    "price": it.get("price")
                    if it.get("price") is not None
                    else cur.get("price"),
                    "source": (cur.get("source") or "") + "|" + (it.get("source") or ""),
                }
        final[key] = list(by.values())
        priced = [i for i in final[key] if i.get("price")]
        print(f"=== {key} total={len(final[key])} priced={len(priced)}")
        for it in sorted(
            priced, key=lambda x: x["price"]
        )[:12]:
            print(f"  R${it['price']:.2f}\t{it.get('title')}\t{it['url']}")

    OUT.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print("saved", OUT)


if __name__ == "__main__":
    main()
