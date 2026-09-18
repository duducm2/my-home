"""Playwright price sweep for Leroy Merlin Brasil — writes cluster-*.json files."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "data" / "research" / "leroymerlin"
CHECKED_AT = date.today().isoformat()
LOCATION = "nova_odessa_cep_13380"
BASE = "https://www.leroymerlin.com.br"

PRODUCT_RE = re.compile(r"^https://www\.leroymerlin\.com\.br/[^/?#]+_\d+$", re.I)
PRICE_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")

# expense_id -> (item, unit, queries, must_include_any, must_exclude_any, unit_hint)
SEARCH_PLAN: dict[str, dict[str, Any]] = {
    # structural
    "EXP_0014": {
        "item": "Impermeabilizante (bianco)",
        "unit": "balde",
        "queries": ["bianco vedacit 18 litros", "bianco vedacit balde"],
        "include": ["bianco"],
        "exclude": [],
        "prefer_package": "18",
    },
    "EXP_0015": {
        "item": "Areia grossa, fina e pedrisco",
        "unit": "metro cúbico (m³)",
        "queries": ["areia metro cubico", "areia m3"],
        "include": ["areia"],
        "exclude": [],
        "require_m3": True,
    },
    "EXP_0016": {
        "item": "Cimento",
        "unit": "saco (50 kg)",
        "queries": ["cimento 50kg"],
        "include": ["cimento", "50"],
        "exclude": ["argamassa", "rejunte"],
    },
    "EXP_0017": {
        "item": "Telha",
        "unit": "unidade",
        "queries": ["telha ceramica portuguesa", "telha ceramica"],
        "include": ["telha"],
        "exclude": ["cumeeira", "parafuso", "kit", "transparente", "pvc", "fibrocimento"],
    },
    "EXP_0019": {
        "item": "Tijolinho de barro",
        "unit": "unidade",
        "queries": ["tijolo comum", "tijolinho barro"],
        "include": ["tijolo"],
        "exclude": ["aparente", "revestimento", "ceramica", "porcelanato", "ecologico"],
    },
    "EXP_0021": {
        "item": "Arame recuzido",
        "unit": "quilograma (kg)",
        "queries": ["arame recozido 1kg", "arame recozido"],
        "include": ["arame", "recoz"],
        "exclude": ["farhado", "liso galvanizado", "inelastico"],
    },
    "EXP_0042": {
        "item": "Madeiramento ou estrutura metálica",
        "unit": "metro quadrado (m²)",
        "queries": ["estrutura metalica telhado m2", "tesoura metalica telhado"],
        "include": ["estrutura", "tesoura", "madeira"],
        "exclude": [],
        "require_m2": True,
    },
    # finishes
    "EXP_0023": {
        "item": "Porcelanato",
        "unit": "metro quadrado (m²)",
        "queries": ["porcelanato 60x60", "piso porcelanato"],
        "include": ["porcelanato"],
        "exclude": ["adesivo", "rejunte", "argamassa", "rodape"],
    },
    "EXP_0024": {
        "item": "Rejunte de porcelanato",
        "unit": "quilograma (kg)",
        "queries": ["rejunte porcelanato 1kg", "rejunte acrilico"],
        "include": ["rejunte"],
        "exclude": ["argamassa", "porcelanato 60"],
    },
    "EXP_0025": {
        "item": "Argamassa para o porcelanato",
        "unit": "saco (20 kg)",
        "queries": ["argamassa porcelanato 20kg", "argamassa aciii 20kg"],
        "include": ["argamassa"],
        "exclude": ["rejunte", "chapisco"],
    },
    "EXP_0041": {
        "item": "Rodapés para acompanhar o porcelanato (R$1500)",
        "unit": "metro linear (m)",
        "queries": ["rodape porcelanato", "rodape ceramico"],
        "include": ["rodape", "rodapé"],
        "exclude": ["cola", "cantoneira"],
    },
    "EXP_0046": {
        "item": "Tinta",
        "unit": "lata (18 L)",
        "queries": ["tinta acrilica 18 litros", "tinta 18L"],
        "include": ["tinta", "18"],
        "exclude": ["esmalte", "spray", "3,6", "3.6", "900"],
    },
    "EXP_0048": {
        "item": "Silicone, espuma expansiva, selante PU",
        "unit": "kit",
        "queries": ["espuma expansiva", "silicone acetico", "selante pu"],
        "include": ["silicone", "espuma", "selante"],
        "exclude": [],
        "kit_mode": True,
    },
    "EXP_0049": {
        "item": "Lona para proteção da obra",
        "unit": "metro quadrado (m²)",
        "queries": ["lona preta protecao", "lona plastica preta"],
        "include": ["lona"],
        "exclude": ["piscina", "tenda"],
    },
    # openings
    "EXP_0026": {
        "item": "Portas internas",
        "unit": "unidade",
        "queries": ["folha de porta madeira lisa 80cm", "porta interna madeira lisa"],
        "include": ["porta"],
        "exclude": ["fechadura", "dobradica", "kit porta pronta", "balcao", "externa", "pivotante"],
    },
    "EXP_0027": {
        "item": "Porta Balcão (R$2000)",
        "unit": "unidade",
        "queries": ["porta balcao aluminio", "porta de correr aluminio 2 folhas"],
        "include": ["porta", "balc"],
        "exclude": ["fechadura", "kit"],
        "alt_include": [["porta", "correr", "aluminio"], ["porta", "correr", "alumínio"]],
    },
    "EXP_0029": {
        "item": "Janela (quartos e escritório)",
        "unit": "unidade",
        "queries": ["janela de correr aluminio 4 folhas 120x120", "janela aluminio 4 folhas"],
        "include": ["janela"],
        "exclude": ["vitro", "vitrô", "basculante", "persiana"],
    },
    "EXP_0030": {
        "item": "Vitrô Sala",
        "unit": "unidade",
        "queries": ["vitro basculante 60x60", "vitrô aluminio 60"],
        "include": ["vitro", "vitrô", "basculante"],
        "exclude": ["janela de correr 4"],
    },
    "EXP_0031": {
        "item": "Vitrôs banheiros",
        "unit": "unidade",
        "queries": ["vitro basculante 40x40", "vitrô banheiro 60x40"],
        "include": ["vitro", "vitrô", "basculante"],
        "exclude": [],
    },
    # plumbing
    "EXP_0028": {
        "item": "Vaso",
        "unit": "unidade",
        "queries": ["vaso sanitario com caixa acoplada", "bacia sanitaria caixa acoplada"],
        "include": ["vaso", "bacia"],
        "exclude": ["assento", "caixa acoplada avulsa", "kit reparo"],
    },
    "EXP_0036": {
        "item": "Torneiras",
        "unit": "unidade",
        "queries": ["torneira lavatorio", "torneira cozinha"],
        "include": ["torneira"],
        "exclude": ["filtro", "arejador avulso"],
    },
    "EXP_0037": {
        "item": "Sifões e ralos",
        "unit": "unidade",
        "queries": ["sifao universal", "sifão copo"],
        "include": ["sifao", "sifão"],
        "exclude": [],
    },
    "EXP_0039": {
        "item": "Pias e bancadas",
        "unit": "conjunto",
        "queries": ["cuba inox cozinha", "pia inox 120cm"],
        "include": ["cuba", "pia"],
        "exclude": ["valvula", "sifao", "torneira"],
    },
    "EXP_0040": {
        "item": "Box de vidro para o banheiro (R$850)",
        "unit": "unidade",
        "queries": ["box banheiro vidro temperado", "box de canto vidro"],
        "include": ["box"],
        "exclude": ["kit roldana", "perfil avulso", "adesivo"],
    },
    "EXP_0044": {
        "item": "Caixa de água",
        "unit": "unidade",
        "queries": ["caixa dagua 1000 litros", "caixa de agua 500 litros"],
        "include": ["caixa"],
        "exclude": ["boia", "tampa avulsa"],
    },
    # electrical
    "EXP_0033": {
        "item": "Quadro de distribuição",
        "unit": "unidade",
        "queries": ["quadro de distribuicao embutir", "quadro distribuicao 12 disjuntores"],
        "include": ["quadro"],
        "exclude": ["disjuntor avulso", "barramento"],
    },
    "EXP_0034": {
        "item": "Conduítes",
        "unit": "metro linear (m)",
        "queries": ["eletroduto corrugado 25mm", "conduíte 3/4"],
        "include": ["eletroduto", "conduit", "conduíte", "corru"],
        "exclude": [],
    },
    "EXP_0035": {
        "item": "Lâmpadas",
        "unit": "unidade",
        "queries": ["lampada led bulbo 9w", "lâmpada led 9w"],
        "include": ["lampada", "lâmpada", "led"],
        "exclude": ["luminaria", "spot", "painel"],
    },
    "EXP_0038": {
        "item": "Tomadas",
        "unit": "unidade",
        "queries": ["tomada 2p+t 10a", "tomada plug 10a"],
        "include": ["tomada"],
        "exclude": ["interruptor", "placa avulsa", "extensao"],
    },
    "EXP_0045": {
        "item": "Dispositivos de segurança",
        "unit": "conjunto",
        "queries": ["kit camera seguranca", "alarme residencial kit"],
        "include": ["camera", "alarme", "segurança", "seguranca"],
        "exclude": [],
    },
    # tools
    "EXP_0018": {
        "item": "Ferramentas",
        "unit": "conjunto",
        "queries": ["kit ferramentas tramontina", "jogo ferramentas manuais"],
        "include": ["kit", "jogo", "ferrament"],
        "exclude": ["eletrica", "furadeira"],
    },
    "EXP_0020": {
        "item": "Carrinho de mão",
        "unit": "unidade",
        "queries": ["carrinho de mao", "carrinho de mão obra"],
        "include": ["carrinho"],
        "exclude": ["bebe", "praia", "supermercado"],
    },
    "EXP_0022": {
        "item": "Caçamba de entulho",
        "unit": "caçamba",
        "queries": ["cacamba entulho aluguel", "caçamba entulho"],
        "include": ["cacamba", "caçamba"],
        "exclude": [],
        "likely_no_match": True,
    },
    "EXP_0043": {
        "item": "Calhas e rufos",
        "unit": "metro linear (m)",
        "queries": ["calha galvanizada", "rufo galvanizado"],
        "include": ["calha", "rufo"],
        "exclude": [],
    },
    "EXP_0047": {
        "item": "Pregos, parafusos, buchas",
        "unit": "pacote",
        "queries": ["kit parafuso bucha", "prego 17x21 pacote"],
        "include": ["prego", "parafuso", "bucha"],
        "exclude": [],
    },
}

CLUSTERS = {
    "structural": [
        "EXP_0014",
        "EXP_0015",
        "EXP_0016",
        "EXP_0017",
        "EXP_0019",
        "EXP_0021",
        "EXP_0042",
    ],
    "finishes": [
        "EXP_0023",
        "EXP_0024",
        "EXP_0025",
        "EXP_0041",
        "EXP_0046",
        "EXP_0048",
        "EXP_0049",
    ],
    "openings": ["EXP_0026", "EXP_0027", "EXP_0029", "EXP_0030", "EXP_0031"],
    "plumbing": [
        "EXP_0028",
        "EXP_0036",
        "EXP_0037",
        "EXP_0039",
        "EXP_0040",
        "EXP_0044",
    ],
    "electrical": ["EXP_0033", "EXP_0034", "EXP_0035", "EXP_0038", "EXP_0045"],
    "tools_logistics": [
        "EXP_0018",
        "EXP_0020",
        "EXP_0022",
        "EXP_0043",
        "EXP_0047",
    ],
}


def parse_price(text: str) -> float | None:
    matches = PRICE_RE.findall(text.replace("\xa0", " "))
    if not matches:
        return None
    # last match is usually the current/promo price; prefer lowest among found
    values = []
    for raw in matches:
        values.append(float(raw.replace(".", "").replace(",", ".")))
    return min(values) if values else None


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"https://www.leroymerlin.com.br{path}"


def text_matches(name: str, plan: dict[str, Any]) -> bool:
    lower = name.lower()
    includes = plan.get("include") or []
    if includes and not any(tok.lower() in lower for tok in includes):
        alt = plan.get("alt_include") or []
        if alt:
            if not any(all(tok.lower() in lower for tok in group) for group in alt):
                return False
        else:
            return False
    for tok in plan.get("exclude") or []:
        if tok.lower() in lower:
            return False
    if plan.get("require_m3") and not any(
        x in lower for x in ("m³", "m3", "metro cúbico", "metro cubico")
    ):
        return False
    if plan.get("require_m2") and not any(
        x in lower for x in ("m²", "m2", "metro quadrado")
    ):
        # allow structural steel/wood sold by piece if clearly structure — still require m2 pricing later
        pass
    return True


def extract_search_products(page) -> list[dict[str, Any]]:
    return page.evaluate(
        """() => {
      const out = [];
      const seen = new Set();
      const anchors = [...document.querySelectorAll('a[href]')].filter(a => /_\\d{5,}$/.test(a.pathname));
      for (const a of anchors) {
        const url = a.href.split('?')[0];
        if (seen.has(url)) continue;
        seen.add(url);
        let el = a;
        let block = '';
        let name = (a.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean)[0] || '';
        for (let i = 0; i < 8 && el; i++) {
          const t = el.innerText || '';
          if (t.includes('R$')) { block = t; break; }
          el = el.parentElement;
        }
        if (!name) {
          const h = (el && el.querySelector('h3,h2')) ? el.querySelector('h3,h2').innerText : '';
          name = (h || a.getAttribute('title') || a.pathname).trim();
        }
        const sku = (url.match(/_(\\d+)$/) || [])[1] || '';
        out.push({ name, sku, url, block });
      }
      return out;
    }"""
    )


def verify_product(page, url: str) -> dict[str, Any] | None:
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1800)
        status = resp.status if resp else 0
        if status != 200:
            return None
        final = normalize_url(page.url)
        if not PRODUCT_RE.match(final):
            return None
        data = page.evaluate(
            """() => {
          const title = document.querySelector('h1')?.innerText?.trim() || document.title;
          const body = document.body?.innerText || '';
          const sellerMatch = body.match(/Vendido\\s+(e\\s+entregue\\s+)?por\\s+([^\\n]+)/i);
          return {
            title,
            bodySample: body.slice(0, 2500),
            seller: sellerMatch ? sellerMatch[2].trim().slice(0, 80) : 'Leroy Merlin'
          };
        }"""
        )
        price = parse_price(data["bodySample"])
        if price is None:
            # try broader page text
            price = parse_price(page.inner_text("body"))
        if price is None:
            return None
        sku = (final.rsplit("_", 1)[-1] if "_" in final else data.get("sku") or "")
        return {
            "matched_product": data["title"].split("\n")[0].strip()[:180],
            "sku": sku,
            "seller": data.get("seller") or "Leroy Merlin",
            "displayed_price_brl": price,
            "product_url": final,
            "final_url": final,
            "http_status": 200,
        }
    except Exception:
        return None


def pick_candidates(
    page, plan: dict[str, Any], max_verify: int = 4
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for query in plan["queries"]:
        search_url = f"{BASE}/search?term={quote(query)}&searchTerm={quote(query)}&searchType=default"
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2200)
        except Exception:
            continue
        raw = extract_search_products(page)
        for item in raw:
            url = normalize_url(item["url"])
            if url in seen_urls:
                continue
            name = item.get("name") or ""
            if not name:
                # derive from slug
                slug = urlparse(url).path.strip("/").rsplit("_", 1)[0]
                name = slug.replace("-", " ")
            if not text_matches(name, plan):
                continue
            price = parse_price(item.get("block") or "")
            seen_urls.add(url)
            collected.append(
                {
                    "name": name,
                    "sku": item.get("sku") or "",
                    "url": url,
                    "list_price": price,
                }
            )
        if len(collected) >= 8:
            break

    # kit mode: keep lowest of silicone / espuma / selante as a representative kit component set
    if plan.get("kit_mode"):
        groups = {"silicone": [], "espuma": [], "selante": []}
        for c in collected:
            n = c["name"].lower()
            if "espuma" in n:
                groups["espuma"].append(c)
            elif "silicone" in n:
                groups["silicone"].append(c)
            elif "selante" in n or "pu" in n:
                groups["selante"].append(c)
        collected = []
        for key in ("silicone", "espuma", "selante"):
            group = [g for g in groups[key] if g.get("list_price")]
            if group:
                collected.append(min(group, key=lambda x: x["list_price"]))

    # sort by list price when available
    collected.sort(key=lambda x: (x["list_price"] is None, x["list_price"] or 1e9))

    verified: list[dict[str, Any]] = []
    for cand in collected[:max_verify]:
        detail = verify_product(page, cand["url"])
        if not detail:
            continue
        # re-check name filters on PDP title
        if not text_matches(detail["matched_product"], plan) and not plan.get("kit_mode"):
            continue
        if plan.get("require_m3"):
            title = detail["matched_product"].lower()
            if not any(x in title for x in ("m³", "m3", "metro cúbico", "metro cubico")):
                continue
        unit = plan["unit"]
        price = detail["displayed_price_brl"]
        normalized = price
        package_size = ""
        caveats = [
            "Freight not calculated for CEP 13380-000; freight_brl left null."
        ]
        title_l = detail["matched_product"].lower()

        # unit normalizations
        if plan["unit"].startswith("unidade") and re.search(r"(\d+)\s*pe[cç]as", title_l):
            n = int(re.search(r"(\d+)\s*pe[cç]as", title_l).group(1))
            if n > 1:
                normalized = round(price / n, 4)
                package_size = f"{n} peças"
                caveats.insert(0, f"Sold as pack of {n}; normalized per unit.")
        if "m²" in unit or "m2" in unit.lower() or "metro quadrado" in unit:
            # try extract box m2
            m = re.search(r"([\d,\.]+)\s*m[²2]", title_l)
            if m and ("caixa" in title_l or "porcelanato" in title_l or "lona" in title_l):
                area = float(m.group(1).replace(".", "").replace(",", ".")) if "," in m.group(1) else float(m.group(1).replace(",", "."))
                # Brazilian: 2,2m² often written 2,2
                try:
                    area = float(m.group(1).replace(".", "").replace(",", ".")) if m.group(1).count(",") == 1 else float(m.group(1).replace(",", "."))
                except ValueError:
                    area = None
                if area and area > 0 and area < 50:
                    normalized = round(price / area, 4)
                    package_size = f"{area} m²"
                    caveats.insert(0, f"Normalized from package/box area {area} m².")
        if plan.get("prefer_package") and plan["prefer_package"] not in title_l:
            # keep but deprioritize via higher effective sort later
            caveats.append(f"Package may differ from preferred {plan['prefer_package']}.")

        entry = {
            "matched_product": detail["matched_product"],
            "sku": detail["sku"],
            "seller": detail["seller"],
            "specifications": {"source_query": plan["queries"][0]},
            "package_size": package_size or "1",
            "displayed_price_brl": price,
            "normalized_unit_price_brl": normalized,
            "unit": unit,
            "minimum_quantity": 1,
            "bulk_tiers": [],
            "freight_brl": None,
            "availability": "in_stock",
            "location_basis": LOCATION,
            "checked_at": CHECKED_AT,
            "product_url": detail["product_url"],
            "final_url": detail["final_url"],
            "http_status": 200,
            "verification_method": (
                f"Leroy Merlin search + PDP browser verification; HTTP 200 on "
                f"{detail['final_url']}; visible price R${price:.2f}. "
                f"Arithmetic: R${normalized:.2f} per {unit}."
            ),
            "caveats": caveats,
        }
        verified.append(entry)
        time.sleep(0.4)

    verified.sort(key=lambda x: x["normalized_unit_price_brl"])
    return verified


def build_expense(page, expense_id: str) -> dict[str, Any]:
    plan = SEARCH_PLAN[expense_id]
    if plan.get("likely_no_match"):
        candidates = pick_candidates(page, plan, max_verify=2)
        if not candidates:
            return {
                "expense_id": expense_id,
                "requested_item": plan["item"],
                "requested_unit": plan["unit"],
                "match_status": "no_match",
                "candidates": [],
                "winner": None,
                "no_match_reason": (
                    "No purchasable caçamba de entulho product with visible retail "
                    "unit price found on Leroy Merlin (service/rental not sold as SKU)."
                ),
            }
    candidates = pick_candidates(page, plan)
    if plan.get("require_m3") or plan.get("require_m2"):
        # filter strict unit sales
        filtered = []
        for c in candidates:
            title = c["matched_product"].lower()
            if plan.get("require_m3") and not any(
                x in title for x in ("m³", "m3", "metro cúbico", "metro cubico")
            ):
                continue
            if plan.get("require_m2"):
                # only accept if priced meaningfully as m2 coverage product
                if not any(x in title for x in ("m²", "m2", "metro")) and "estrutura" not in title and "tesoura" not in title:
                    continue
            filtered.append(c)
        if plan.get("require_m3"):
            candidates = filtered
        elif plan.get("require_m2") and not filtered:
            return {
                "expense_id": expense_id,
                "requested_item": plan["item"],
                "requested_unit": plan["unit"],
                "match_status": "no_match",
                "candidates": candidates[:3],
                "winner": None,
                "no_match_reason": (
                    "No clear m²-priced madeiramento/estrutura metálica package found; "
                    "only linear lumber or unrelated SKUs with non-comparable units."
                ),
            }
        elif plan.get("require_m2"):
            candidates = filtered

    if not candidates:
        reason = (
            "No comparable product with visible price verified on a direct "
            "leroymerlin.com.br product page for this unit."
        )
        if plan.get("require_m3"):
            reason = (
                "Only bagged aggregates found; no m³-priced bulk areia/pedrisco "
                "with a verified product-page unit price."
            )
        return {
            "expense_id": expense_id,
            "requested_item": plan["item"],
            "requested_unit": plan["unit"],
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": reason,
        }

    # kit: sum three components if available, else lowest single component with caveat
    if plan.get("kit_mode") and len(candidates) >= 2:
        total = round(sum(c["displayed_price_brl"] for c in candidates[:3]), 2)
        names = " + ".join(c["matched_product"] for c in candidates[:3])
        winner = {
            **candidates[0],
            "matched_product": f"Kit representativo: {names}"[:220],
            "displayed_price_brl": total,
            "normalized_unit_price_brl": total,
            "package_size": f"{min(3, len(candidates))} itens",
            "product_url": candidates[0]["product_url"],
            "final_url": candidates[0]["final_url"],
            "verification_method": (
                "Sum of lowest verified silicone/espuma/selante component PDP prices "
                f"on Leroy Merlin (= R${total:.2f}). Primary URL is first component."
            ),
            "caveats": [
                "Representative kit assembled from lowest verified individual components.",
                "Freight not calculated for CEP 13380-000; freight_brl left null.",
            ],
            "specifications": {
                "components": [
                    {
                        "name": c["matched_product"],
                        "price": c["displayed_price_brl"],
                        "url": c["final_url"],
                    }
                    for c in candidates[:3]
                ]
            },
        }
        return {
            "expense_id": expense_id,
            "requested_item": plan["item"],
            "requested_unit": plan["unit"],
            "match_status": "verified",
            "candidates": candidates,
            "winner": winner,
            "no_match_reason": "",
        }

    winner = candidates[0]
    # prefer preferred package size when close
    prefer = plan.get("prefer_package")
    if prefer:
        preferred = [
            c
            for c in candidates
            if prefer in c["matched_product"].lower()
            or prefer.replace(",", ".") in c["matched_product"].lower()
        ]
        if preferred:
            winner = min(preferred, key=lambda x: x["normalized_unit_price_brl"])

    return {
        "expense_id": expense_id,
        "requested_item": plan["item"],
        "requested_unit": plan["unit"],
        "match_status": "verified",
        "candidates": candidates,
        "winner": winner,
        "no_match_reason": "",
    }


def run_cluster(page, cluster: str, expense_ids: list[str]) -> dict[str, Any]:
    expenses = []
    for expense_id in expense_ids:
        print(f"[{cluster}] {expense_id} ...", flush=True)
        expenses.append(build_expense(page, expense_id))
    return {
        "cluster": cluster,
        "checked_at": CHECKED_AT,
        "location_basis": LOCATION,
        "expenses": expenses,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import sys

    only = sys.argv[1] if len(sys.argv) > 1 else None
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            locale="pt-BR",
            geolocation={"latitude": -22.7772, "longitude": -47.2963},
            permissions=["geolocation"],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        for cluster, ids in CLUSTERS.items():
            if only and cluster != only:
                continue
            doc = run_cluster(page, cluster, ids)
            path = OUT_DIR / f"cluster-{cluster}.json"
            path.write_text(
                json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(f"Wrote {path}", flush=True)
        browser.close()


if __name__ == "__main__":
    main()
