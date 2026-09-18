"""Fetch Leroy Merlin product pages via jina.ai HTTP reader and extract prices."""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.request
from pathlib import Path

ctx = ssl.create_default_context()
OUT = Path(
    r"C:\Users\eduev\Meu Drive\17 - Projects\my-home\data\research\leroymerlin\_tmp_finishes_fetched.json"
)

# candidates: expense_id -> list of (path_slug_id, notes)
CANDIDATES: dict[str, list[tuple[str, str]]] = {
    "EXP_0025": [
        ("argamassa-aciii-interno-e-externo-20kg-cinza-axton_89296172", "Axton cinza"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-votomassa-votorantim_87125962", "Votomassa cinza"),
        ("argamassa-aciii-interno-e-externo-20kg-branco-votomassa-votorantim_87912153", "Votomassa branco"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-cimentcola-flexivel-quartzolit_89684140", "Quartzolit flex"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-mg-massa_92524775", "Mg Massa"),
        ("argamassa-aciii-interno-e-externo-20kg-branco-cimentcola-quartzolit_90985930", "Quartzolit branco"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-br-massa_89229791", "BR Massa"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-axton_89820234", "Axton CDN alt id"),
        ("argamassa-colante-aciii-cinza-20kg-precon_86857680", "Precon"),
        ("argamassa-aciii-flex-interno-e-externo-cinza-20kg-argalit_90609092", "Argalit"),
        ("argamassa-colante-aciii-porcelanato-20kg_92173144", "MassaForte porcelanato"),
        ("argamassa-aciii-interno-e-externo-20kg-ultra-flexivel-m29-hp-cinza-mc-bauchemie_92394743", "M29 HP"),
    ],
    "EXP_0024": [
        ("rejunte-acrilico-branco-1-kg-quartzolit_91931840", "Quartzolit branco"),
        ("rejunte-acrilico-corda-1-kg-quartzolit_91931875", "Quartzolit corda"),
        ("rejunte-acrilico-marfim-1kg-portobello_92367394", "Portobello marfim"),
        ("rejunte-acrilico-camurca-1kg-fortaleza_92380953", "Fortaleza camurça"),
        ("rejunte-acrilico-fortaleza-1kg-chocolate_1570939729", "Fortaleza chocolate"),
        ("rejunte-acrilico-rejunte-base-plastica-cinza-platina-1kg-axton_92108380", "Axton platina"),
        ("rejunte-acrilico-rejunte-base-plastica-areia-1kg-axton_92108611", "Axton areia"),
        ("rejunte-para-areas-umidas-acrilico-marfim-1kg-axton_90537251", "Axton premium marfim"),
        ("rejunte-acrilico-1kg-cafe-fortaleza_1571039551", "Fortaleza café"),
        ("rejunte-acrilico-branco-1kg-axton_90537244", "Axton branco guess"),
        ("rejunte-acrilico-1kg-pronto-branco_90350899", "Pronto branco guess"),
        ("rejunte-acrilico-branco-1kg-axton_92108373", "Axton branco guess2"),
    ],
    "EXP_0023": [
        ("porcelanato-60x60_0", "placeholder skip"),
    ],
}

# Extra searches via known slug patterns from Bing CDN later for other expenses
EXTRA = {
    "EXP_0046": [
        ("tinta-acrilica-fosco-branco-18l-coral_88401234", "guess"),
    ],
}


def jina_fetch(product_path: str) -> dict:
    # Prefer http which sometimes yields more content
    src = f"http://www.leroymerlin.com.br/{product_path}"
    url = f"https://r.jina.ai/{src}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/markdown",
            "X-Return-Format": "markdown",
        },
    )
    with urllib.request.urlopen(req, timeout=70, context=ctx) as r:
        text = r.read().decode("utf-8", "replace")
        status = r.status
    prices = re.findall(r"R\$\s*([\d.]+,\d{2})", text)
    prices_f = []
    for p in prices:
        prices_f.append(float(p.replace(".", "").replace(",", ".")))
    captcha = "CAPTCHA" in text or "Verification Required" in text
    title_m = re.search(r"^Title:\s*(.+)$", text, re.M)
    title = title_m.group(1).strip() if title_m else ""
    # availability hints
    avail = None
    if re.search(r"Indispon[ií]vel|OutOfStock|esgotado", text, re.I):
        avail = "out_of_stock"
    elif re.search(r"InStock|Dispon[ií]vel|Adicionar ao carrinho|Comprar", text, re.I):
        avail = "in_stock"
    return {
        "http_status": status,
        "product_path": product_path,
        "product_url": f"https://www.leroymerlin.com.br/{product_path}",
        "title": title,
        "prices_brl": prices_f[:20],
        "min_price": min(prices_f) if prices_f else None,
        "captcha": captcha,
        "availability_hint": avail,
        "sample": text[:1200],
        "len": len(text),
    }


results: dict[str, list] = {}
all_items = []
for exp, items in CANDIDATES.items():
    if exp == "EXP_0023":
        continue
    results[exp] = []
    for path, note in items:
        print(f"FETCH {exp} {path} ({note})")
        try:
            data = jina_fetch(path)
            data["note"] = note
            data["expense_id"] = exp
            results[exp].append(data)
            print(
                "  ->",
                "captcha" if data["captcha"] else "ok",
                "min",
                data["min_price"],
                "title",
                (data["title"] or "")[:70],
                "len",
                data["len"],
            )
        except Exception as e:
            print("  ERR", type(e).__name__, e)
            results[exp].append(
                {
                    "expense_id": exp,
                    "product_path": path,
                    "note": note,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
        time.sleep(1.2)

OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("Wrote", OUT)
