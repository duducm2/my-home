"""Decode Bing shopping offers and verify LM prices via Jina."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).with_name("_tmp_tools_verified.json")

CANDIDATES = [
    # EXP_0018 tool kits
    (
        "EXP_0018",
        "https://www.leroymerlin.com.br/maleta-kit-jogo-ferramentas-gerais-utilidades-uso-domestico-9-pecas-8009c_1570679472",
    ),
    (
        "EXP_0018",
        "https://www.leroymerlin.com.br/maleta-kit-jogo-ferramentas-gerais-utilidades-uso-domestico-13-pecas-8013c_1570679471",
    ),
    (
        "EXP_0018",
        "https://www.leroymerlin.com.br/kit-de-ferramentas-sparta-aco-carbono-com-maleta-129-pecas_89954333",
    ),
    (
        "EXP_0018",
        "https://www.leroymerlin.com.br/jogo-de-ferramentas-29-pecas-dexter_92465933",
    ),
    (
        "EXP_0018",
        "https://www.leroymerlin.com.br/jogo-de-ferramentas-profissional-200-pecas-titanium_90944672",
    ),
    (
        "EXP_0018",
        "https://www.leroymerlin.com.br/jogo-de-ferramenta-com-maleta-200-pecas-preta_1572737131",
    ),
    # EXP_0020 wheelbarrows
    (
        "EXP_0020",
        "https://www.leroymerlin.com.br/carrinho-de-mao-em-aco-carbono-pneu-macico-chapa-26mm-45l_1571958083",
    ),
    (
        "EXP_0020",
        "https://www.leroymerlin.com.br/carrinho-de-mao-em-aco-carbono-pneu-macico-chapa-26mm-45l_1571958083",
    ),
    # EXP_0043 calhas/rufos
    (
        "EXP_0043",
        "https://www.leroymerlin.com.br/bobina-galvanizada-20cm-x-3mts-rufo-calha-pingadeira-algerosa_1569336197",
    ),
    (
        "EXP_0043",
        "https://www.leroymerlin.com.br/rufo-calha-galvanizada-90cm-x-2m-em-rolos-bobina-para-pingadeira-ou-algerosa_1572259796",
    ),
    (
        "EXP_0043",
        "https://www.leroymerlin.com.br/bobina-galvanizada-20cm-x-2mts-rufo-calha-pingadeira-algerosa_1569336196",
    ),
    # fasteners guesses + searches later
    (
        "EXP_0047",
        "https://www.leroymerlin.com.br/kit-parafuso-e-bucha-8mm-com-100-pecas_1568000000",
    ),
]


def jina_fetch(url: str) -> dict:
    clean = url.split("?")[0].rstrip("/")
    ju = "https://r.jina.ai/" + clean
    req = urllib.request.Request(
        ju,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/plain",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", "replace")
    prices = re.findall(r"R\$\s*([\d.]+,\d{2})", raw)
    title_m = re.search(r"Title:\s*(.+)", raw)
    # Prefer first product price; convert BR format
    parsed = []
    for p in prices:
        n = float(p.replace(".", "").replace(",", "."))
        parsed.append(n)
    return {
        "product_url": clean,
        "title": title_m.group(1).strip() if title_m else None,
        "prices_brl": parsed[:15],
        "raw_len": len(raw),
        "snippet": raw[:2500],
    }


def bing_find(query: str) -> list[str]:
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query) + "&count=30"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", "replace")
    except Exception as exc:
        print("bing err", query, exc)
        return []
    return list(
        dict.fromkeys(
            re.findall(
                r"https://www\.leroymerlin\.com\.br/[a-zA-Z0-9\-_%]+_\d+", html, re.I
            )
        )
    )


def main() -> None:
    extra_queries = [
        "site:leroymerlin.com.br rufo interno 300cm",
        "site:leroymerlin.com.br bobina galvanizada 20cm",
        "site:leroymerlin.com.br kit parafuso bucha",
        "site:leroymerlin.com.br parafuso bucha nylon kit",
        "site:leroymerlin.com.br prego com cabeca 17x21",
        "site:leroymerlin.com.br prego 18x27 pacote",
        "site:leroymerlin.com.br caçamba entulho",
        "site:leroymerlin.com.br carrinho de mao 65l tramontina",
        "site:leroymerlin.com.br carrinho de mao cacamba plastica 60",
    ]
    extras: list[tuple[str, str]] = []
    for q in extra_queries:
        urls = bing_find(q)
        print("bing", q[:50], len(urls))
        for u in urls[:6]:
            print(" ", u)
            exp = "EXP_0047"
            if "carrinho" in u:
                exp = "EXP_0020"
            elif any(x in u for x in ("calha", "rufo", "bobina", "pingadeira")):
                exp = "EXP_0043"
            elif "cacamba" in u or "caçamba" in u or "entulho" in u:
                exp = "EXP_0022"
            elif any(x in u for x in ("ferrament", "maleta", "jogo-de")):
                exp = "EXP_0018"
            extras.append((exp, urllib.parse.unquote(u)))

    seen = set()
    results = []
    for exp, url in CANDIDATES + extras:
        url = url.split("?")[0]
        if url in seen:
            continue
        seen.add(url)
        # skip obviously fake guessed id
        if url.endswith("_1568000000"):
            continue
        print("fetch", exp, url)
        try:
            data = jina_fetch(url)
            data["expense_id"] = exp
            print(" ", data["title"], data["prices_brl"][:5])
            results.append(data)
        except Exception as exc:
            print("  ERR", type(exc).__name__, exc)
            results.append(
                {
                    "expense_id": exp,
                    "product_url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT, "n=", len(results))


if __name__ == "__main__":
    main()
