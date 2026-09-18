"""Fetch fastener candidates from LM category pages via Jina."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).with_name("_tmp_fasteners.json")


def fetch(url: str) -> str:
    req = urllib.request.Request(
        "https://r.jina.ai/" + url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def brl(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def main() -> None:
    pages = [
        "https://www.leroymerlin.com.br/pregos",
        "https://www.leroymerlin.com.br/buchas",
        "https://www.leroymerlin.com.br/parafusos",
        "https://www.leroymerlin.com.br/kits-de-fixacao",
    ]
    product_urls: list[str] = []
    for page in pages:
        try:
            raw = fetch(page)
        except Exception as exc:
            print("page ERR", page, exc)
            continue
        found = list(
            dict.fromkeys(
                re.findall(
                    r"https://www\.leroymerlin\.com\.br/[a-z0-9\-]+_\d+", raw, re.I
                )
            )
        )
        print(page.split("/")[-1], "n", len(found))
        for u in found[:40]:
            if any(
                x in u
                for x in (
                    "prego",
                    "parafuso",
                    "bucha",
                    "kit",
                    "fixacao",
                    "fixação",
                )
            ):
                print(" ", u)
                product_urls.append(u)

    # prioritize likely packages
    prioritize = [
        u
        for u in product_urls
        if any(
            x in u
            for x in (
                "kit",
                "100-pecas",
                "pacote",
                "1kg",
                "500g",
                "bucha",
                "17x21",
                "18x27",
            )
        )
    ]
    rest = [u for u in product_urls if u not in prioritize]
    sample = list(dict.fromkeys(prioritize + rest))[:18]

    results = []
    for u in sample:
        print("fetch", u.split("/")[-1])
        try:
            raw = fetch(u)
        except Exception as exc:
            print("  ERR", exc)
            results.append({"url": u, "error": str(exc)})
            continue
        title_m = re.search(r"Title:\s*(.+)", raw)
        title = title_m.group(1).strip() if title_m else ""
        prices = [brl(p) for p in re.findall(r"R\$\s*([\d.]+,\d{2})", raw)[:8]]
        pix = None
        m = re.search(
            r"R\$\s*([\d.]+,\d{2})\s*(?:à vista no pix|a vista no pix|no pix)",
            raw,
            re.I,
        )
        if m:
            pix = brl(m.group(1))
        # pattern from tools: line 'R$ xx' then 'R$ yy à vista no pix'
        lines = [
            re.sub(r"\s+", " ", ln.strip())
            for ln in raw.splitlines()
            if "R$" in ln
        ][:8]
        print(" ", title[:80], prices[:4], "pix", pix)
        for ln in lines[:5]:
            print("   ", ln[:120])
        results.append(
            {
                "url": u,
                "title": title,
                "prices": prices,
                "pix": pix,
                "lines": lines[:8],
            }
        )

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
