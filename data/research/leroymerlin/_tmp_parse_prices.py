"""Parse Jina LM pages for primary displayed price near product title."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

URLS = [
    "https://www.leroymerlin.com.br/maleta-kit-jogo-ferramentas-gerais-utilidades-uso-domestico-9-pecas-8009c_1570679472",
    "https://www.leroymerlin.com.br/maleta-kit-jogo-ferramentas-gerais-utilidades-uso-domestico-13-pecas-8013c_1570679471",
    "https://www.leroymerlin.com.br/kit-de-ferramentas-sparta-aco-carbono-com-maleta-129-pecas_89954333",
    "https://www.leroymerlin.com.br/jogo-de-ferramentas-29-pecas-dexter_92465933",
    "https://www.leroymerlin.com.br/jogo-de-ferramentas-profissional-200-pecas-titanium_90944672",
    "https://www.leroymerlin.com.br/jogo-de-ferramenta-com-maleta-200-pecas-preta_1572737131",
    "https://www.leroymerlin.com.br/carrinho-de-mao-em-aco-carbono-pneu-macico-chapa-26mm-45l_1571958083",
    "https://www.leroymerlin.com.br/bobina-galvanizada-20cm-x-2mts-rufo-calha-pingadeira-algerosa_1569336251",
    "https://www.leroymerlin.com.br/bobina-galvanizada-20cm-x-3mts-rufo-calha-pingadeira-algerosa_1569336197",
    "https://www.leroymerlin.com.br/rufo-calha-galvanizada-90cm-x-2m-em-rolos-bobina-para-pingadeira-ou-algerosa_1572259796",
]


def brl(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def fetch(url: str) -> str:
    req = urllib.request.Request(
        "https://r.jina.ai/" + url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def main() -> None:
    out = []
    for url in URLS:
        raw = fetch(url)
        title_m = re.search(r"Title:\s*(.+)", raw)
        title = title_m.group(1).strip() if title_m else ""
        # Prefer PIX / sale patterns commonly used on LM
        candidates = []
        for m in re.finditer(
            r"(?:por|Por|no Pix|no PIX|à vista|a vista|Preço|preco)\D{0,40}R\$\s*([\d.]+,\d{2})",
            raw,
            re.I,
        ):
            candidates.append(("ctx", brl(m.group(1)), m.group(0)[:80]))
        # From markdown price lines: **R$ xx,xx**
        for m in re.finditer(r"\*\*R\$\s*([\d.]+,\d{2})\*\*", raw):
            candidates.append(("bold", brl(m.group(1)), m.group(0)))
        # First 5 raw prices
        raw_prices = [brl(p) for p in re.findall(r"R\$\s*([\d.]+,\d{2})", raw)[:8]]
        print(url.split("/")[-1])
        print(" title", title[:90])
        print(" raw", raw_prices)
        print(" cand", candidates[:8])
        # extract section after Markdown Content around first price cluster
        idx = raw.find("Markdown Content:")
        body = raw[idx : idx + 3500] if idx >= 0 else raw[:3500]
        price_lines = [
            re.sub(r"\s+", " ", ln)
            for ln in body.splitlines()
            if "R$" in ln
        ][:12]
        for ln in price_lines:
            print("  L", ln[:160])
        out.append(
            {
                "url": url,
                "title": title,
                "raw_prices": raw_prices,
                "candidates": candidates[:10],
                "price_lines": price_lines,
            }
        )
        print("---")
    Path(__file__).with_name("_tmp_tools_price_parse.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
