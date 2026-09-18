"""Build data/research/leroymerlin/cluster-finishes.json from API results."""
from __future__ import annotations

import json
from pathlib import Path

CHECKED = "2026-09-17"
LOC = "nova_odessa_cep_13380"
OUT = Path(
    r"C:\Users\eduev\Meu Drive\17 - Projects\my-home\data\research\leroymerlin\cluster-finishes.json"
)


def cand(
    *,
    name,
    sku,
    brand,
    specs,
    package_size,
    displayed,
    normalized,
    unit,
    url,
    verification,
    caveats,
    availability="in_stock",
):
    return {
        "matched_product": name,
        "sku": str(sku),
        "seller": "Leroy Merlin",
        "specifications": specs,
        "package_size": package_size,
        "displayed_price_brl": displayed,
        "normalized_unit_price_brl": normalized,
        "unit": unit,
        "minimum_quantity": 1,
        "bulk_tiers": [],
        "freight_brl": None,
        "availability": availability,
        "location_basis": LOC,
        "checked_at": CHECKED,
        "product_url": url,
        "final_url": url,
        "http_status": 200,
        "verification_method": verification,
        "caveats": caveats,
    }


# EXP_0023 porcelain — price.to is R$/m²; pack.price is box
c23 = [
    cand(
        name="Porcelanato Cimentício Acetinado Interno Borda Reta 60x60cm Cimento Toronto",
        sku=92277892,
        brand="Toronto",
        specs={
            "brand": "Toronto",
            "format_cm": "60 x 60",
            "finish": "Acetinado; borda reta",
            "color": "Off White / Cimento",
            "box_area_m2": 2.2,
            "pieces_per_box": 6,
            "use": "Interno",
        },
        package_size="caixa 2,2 m²",
        displayed=103.2,
        normalized=46.91,
        unit="m²",
        url="https://www.leroymerlin.com.br/porcelanato-cimenticio-acetinado-interno-borda-reta-60x60cm-cimento-toronto_92277892",
        verification=(
            "Leroy Merlin api/v3/products/92277892 HTTP 200 with X-Region=campinas "
            "(Nova Odessa/CEP 13380 proxy); pricing.price.to R$46,91/m²; pack.packaging=2,2 m² "
            "and pack.price R$103,20; isAvailableOnEcommerce=true. Arithmetic: 46.91×2.2=103.202≈103.20."
        ),
        caveats=[
            "Lowest verified in-stock per-m² price among available 60x60 porcelain candidates.",
            "Regional price via X-Region=campinas; freight for CEP 13380-000 not calculated.",
        ],
    ),
    cand(
        name="Porcelanato Cimentício Acetinado Interno Borda Reta 60x60cm Paviment Gray Incesa",
        sku=91844543,
        brand="Incesa",
        specs={
            "brand": "Incesa",
            "format_cm": "60 x 60",
            "finish": "Acetinado; borda reta",
            "color": "Gray",
            "box_area_m2": 2.2,
            "pieces_per_box": 6,
            "use": "Interno",
        },
        package_size="caixa 2,2 m²",
        displayed=109.78,
        normalized=49.9,
        unit="m²",
        url="https://www.leroymerlin.com.br/porcelanato-cimenticio-acetinado-interno-borda-reta-60x60cm-paviment-gray-incesa_91844543",
        verification=(
            "api/v3/products/91844543 HTTP 200 X-Region=campinas; pricing.price.to R$49,90/m²; "
            "pack 2,2 m² pack.price R$109,78; isAvailableOnEcommerce=true."
        ),
        caveats=[],
    ),
    cand(
        name="Porcelanato Cimentício Acetinado Interno Borda Reta 61x61cm Beton Gray Artens",
        sku=92098860,
        brand="Artens",
        specs={
            "brand": "Artens",
            "format_cm": "61 x 61",
            "finish": "Acetinado; borda reta",
            "color": "Gray",
            "box_area_m2": 1.87,
            "use": "Interno",
        },
        package_size="caixa 1,87 m²",
        displayed=round(53.49 * 1.87, 2),
        normalized=53.49,
        unit="m²",
        url="https://www.leroymerlin.com.br/porcelanato-cimenticio-acetinado-interno-borda-reta-61x61cm-beton-gray-artens_92098860",
        verification=(
            "api/v3/products/92098860 HTTP 200 X-Region=campinas; pricing.price.to R$53,49/m²; "
            "packaging 1,87 m²; isAvailableOnEcommerce=true. Near-60x60 alternate."
        ),
        caveats=["Format 61x61 cm (near 60x60 preference)."],
    ),
]

# EXP_0024
c24 = [
    cand(
        name="Rejunte Acrílico Areia 1kg Axton",
        sku=92108611,
        brand="Axton",
        specs={
            "brand": "Axton",
            "type": "Acrílico",
            "color": "Areia",
            "weight_kg": 1,
        },
        package_size="1 kg",
        displayed=33.75,
        normalized=33.75,
        unit="kg",
        url="https://www.leroymerlin.com.br/rejunte-acrilico-areia-1kg-axton_92108611",
        verification=(
            "api/v3/products/92108611 HTTP 200 X-Region=campinas; pricing.price.to R$33,75; "
            "characteristics Conteúdo da Embalagem=1 Kg; isAvailableOnEcommerce=true. "
            "Arithmetic: R$33.75 / 1 kg = R$33.75/kg."
        ),
        caveats=[
            "Lowest verified in-stock acrylic 1 kg among candidates (sand color).",
            "Freight for CEP 13380-000 not calculated.",
        ],
    ),
    cand(
        name="Rejunte Acrílico Azul 1kg Axton",
        sku=92108604,
        brand="Axton",
        specs={
            "brand": "Axton",
            "type": "Acrílico",
            "color": "Azul",
            "weight_kg": 1,
        },
        package_size="1 kg",
        displayed=33.75,
        normalized=33.75,
        unit="kg",
        url="https://www.leroymerlin.com.br/rejunte-acrilico-azul-1kg-axton_92108604",
        verification=(
            "api/v3/products/92108604 HTTP 200 X-Region=campinas; pricing.price.to R$33,75; "
            "isAvailableOnEcommerce=true."
        ),
        caveats=["Same unit price as Areia winner; alternate color."],
    ),
    cand(
        name="Rejunte Acrílico Cinza Platina 1 Kg Quartzolit",
        sku=91931833,
        brand="Quartzolit",
        specs={
            "brand": "Quartzolit",
            "type": "Acrílico",
            "color": "Cinza Platina",
            "weight_kg": 1,
        },
        package_size="1 kg",
        displayed=35.2,
        normalized=35.2,
        unit="kg",
        url="https://www.leroymerlin.com.br/rejunte-acrilico-cinza-platina-1-kg-quartzolit_91931833",
        verification=(
            "api/v3/products/91931833 HTTP 200 X-Region=campinas; pricing.price.to R$35,20; "
            "isAvailableOnEcommerce=true."
        ),
        caveats=[],
    ),
]

# EXP_0025
c25 = [
    cand(
        name="Argamassa ACIII Interno e Externo 20kg Cinza Axton",
        sku=89296172,
        brand="Axton",
        specs={
            "brand": "Axton",
            "type": "ACIII",
            "color": "Cinza",
            "weight_kg": 20,
            "use": "Interno/externo; assentamento de revestimento",
        },
        package_size="saco 20 kg",
        displayed=34.9,
        normalized=34.9,
        unit="saco (20 kg)",
        url="https://www.leroymerlin.com.br/argamassa-aciii-interno-e-externo-20kg-cinza-axton_89296172",
        verification=(
            "api/v3/products/89296172 HTTP 200 X-Region=campinas; pricing.price.to R$34,90; "
            "characteristics Peso do Produto=20,00 Kg and Tipo da Argamassa=ACIII; "
            "isAvailableOnEcommerce=true. Arithmetic: R$34.90 / 1 saco = R$34.90/saco."
        ),
        caveats=[
            "Lowest verified in-stock ACIII 20 kg bag among candidates.",
            "Freight for CEP 13380-000 not calculated.",
        ],
    ),
    cand(
        name="Argamassa ACIII Interno e Externo 20kg Cinza Flexível Fortaleza",
        sku=90220144,
        brand="Fortaleza",
        specs={
            "brand": "Fortaleza",
            "type": "ACIII flexível",
            "color": "Cinza",
            "weight_kg": 20,
        },
        package_size="saco 20 kg",
        displayed=35.9,
        normalized=35.9,
        unit="saco (20 kg)",
        url="https://www.leroymerlin.com.br/argamassa-aciii-interno-e-externo-20kg-cinza-flexivel-fortaleza_90220144",
        verification=(
            "api/v3/products/90220144 HTTP 200 X-Region=campinas; pricing.price.to R$35,90; "
            "isAvailableOnEcommerce=true."
        ),
        caveats=[],
    ),
    cand(
        name="Argamassa ACIII Interno e Externo 20kg Cinza Cimentcola Flexível Quartzolit",
        sku=89684140,
        brand="Quartzolit",
        specs={
            "brand": "Quartzolit",
            "type": "ACIII flexível / Cimentcola",
            "color": "Cinza",
            "weight_kg": 20,
        },
        package_size="saco 20 kg",
        displayed=44.9,
        normalized=44.9,
        unit="saco (20 kg)",
        url="https://www.leroymerlin.com.br/argamassa-aciii-interno-e-externo-20kg-cinza-cimentcola-flexivel-quartzolit_89684140",
        verification=(
            "api/v3/products/89684140 HTTP 200 X-Region=campinas; pricing.price.to R$44,90; "
            "isAvailableOnEcommerce=true."
        ),
        caveats=[],
    ),
]

# EXP_0046
c46 = [
    cand(
        name="Tinta Acrílica Fosca para Parede Interna Luxens Econômica Branco 18L",
        sku=91917014,
        brand="Luxens",
        specs={
            "brand": "Luxens",
            "type": "Acrílica econômica fosca",
            "color": "Branco",
            "volume_l": 18,
            "use": "Parede interna",
        },
        package_size="lata 18 L",
        displayed=199.9,
        normalized=199.9,
        unit="lata (18 L)",
        url="https://www.leroymerlin.com.br/tinta-acrilica-fosca-para-parede-interna-luxens-economica-branco-18l_91917014",
        verification=(
            "api/v3/products/91917014 HTTP 200 X-Region=campinas; pricing.price.to R$199,90; "
            "name includes 18L Branco; isAvailableOnEcommerce=true. "
            "Arithmetic: R$199.90 / 1 lata = R$199.90/lata."
        ),
        caveats=[
            "Lowest verified in-stock 18 L white wall acrylic among available candidates.",
            "Freight for CEP 13380-000 not calculated.",
        ],
    ),
    cand(
        name="Tinta Acrílica para Piso Fosca Premium Branca 18 Luxens",
        sku=92136492,
        brand="Luxens",
        specs={
            "brand": "Luxens",
            "type": "Acrílica piso fosca premium",
            "color": "Branca",
            "volume_l": 18,
            "use": "Piso",
        },
        package_size="lata 18 L",
        displayed=249.9,
        normalized=249.9,
        unit="lata (18 L)",
        url="https://www.leroymerlin.com.br/tinta-acrilica-para-piso-fosca-premium-branca-18-luxens_92136492",
        verification=(
            "api/v3/products/92136492 HTTP 200 X-Region=campinas; pricing.price.to R$249,90; "
            "isAvailableOnEcommerce=true."
        ),
        caveats=["Floor paint alternate; not wall acrylic."],
    ),
    cand(
        name="Tinta Acrílica Fosca para Parede Interna Pronto para Uso Luxens Premium Branca 18L",
        sku=91917560,
        brand="Luxens",
        specs={
            "brand": "Luxens",
            "type": "Acrílica fosca premium",
            "color": "Branca",
            "volume_l": 18,
            "use": "Parede interna",
        },
        package_size="lata 18 L",
        displayed=399.9,
        normalized=399.9,
        unit="lata (18 L)",
        url="https://www.leroymerlin.com.br/tinta-acrilica-fosca-para-parede-interna-pronto-para-uso-luxens-premium-branco-18l_91917560",
        verification=(
            "api/v3/products/91917560 HTTP 200 X-Region=campinas; pricing.price.to R$399,90; "
            "isAvailableOnEcommerce=true."
        ),
        caveats=["Premium tier; not lowest qty-1."],
    ),
]

# EXP_0048 kit = silicone + espuma (PU sealant not verified)
sil = cand(
    name="Silicone Acético Uso Geral 260g Transparente Mundialprime",
    sku=1567475755,
    brand="Mundial Prime",
    specs={"brand": "Mundial Prime", "type": "Silicone acético uso geral", "net_g": 260},
    package_size="tubo 260 g",
    displayed=15.62,
    normalized=15.62,
    unit="unidade",
    url="https://www.leroymerlin.com.br/silicone-acetico-uso-geral-260g-transparente-mundialprime_1567475755",
    verification=(
        "api/v3/products/1567475755 HTTP 200 X-Region=campinas; pricing.price.to R$15,62; "
        "isAvailableOnEcommerce=true."
    ),
    caveats=[],
)
esp = cand(
    name="Espuma Expansiva 320Gr Tek Bond",
    sku=89796392,
    brand="Tek Bond",
    specs={"brand": "Tek Bond", "type": "Espuma expansiva PU", "net_g": 320},
    package_size="lata 320 g",
    displayed=19.9,
    normalized=19.9,
    unit="unidade",
    url="https://www.leroymerlin.com.br/espuma-expansiva-320gr-tek-bond_89796392",
    verification=(
        "api/v3/products/89796392 HTTP 200 X-Region=campinas; pricing.price.to R$19,90; "
        "isAvailableOnEcommerce=true."
    ),
    caveats=[],
)
kit_total = round(15.62 + 19.9, 2)
c48_kit = cand(
    name=(
        "Kit 2 produtos (selante PU não encontrado com preço verificável): "
        "Silicone Acético Uso Geral 260g Transparente Mundialprime + "
        "Espuma Expansiva 320Gr Tek Bond"
    ),
    sku="1567475755+89796392",
    brand="mixed",
    specs={
        "components": [
            {"sku": "1567475755", "role": "silicone", "price_brl": 15.62},
            {"sku": "89796392", "role": "espuma_expansiva", "price_brl": 19.9},
        ],
        "missing_component": "selante PU",
    },
    package_size="kit 2 itens",
    displayed=kit_total,
    normalized=kit_total,
    unit="kit",
    url="https://www.leroymerlin.com.br/silicone-acetico-uso-geral-260g-transparente-mundialprime_1567475755",
    verification=(
        "Sum of lowest verified in-stock silicone + espuma via api/v3/products "
        "(1567475755 R$15,62 + 89796392 R$19,90) with X-Region=campinas. "
        "Arithmetic: 15.62+19.90=35.52. No in-stock selante PU with verifiable API price found."
    ),
    caveats=[
        "Representative kit uses lowest verified silicone + espuma only; selante PU component not verified.",
        "product_url points to silicone component page; espuma URL recorded in component specs.",
        "Freight for CEP 13380-000 not calculated.",
    ],
)

# EXP_0049
c49 = [
    cand(
        name="Bobina de Lona Plástica 4x10m Preta Plasitap",
        sku=92450225,
        brand="Plasitap",
        specs={
            "brand": "Plasitap",
            "color": "Preta",
            "width_m": 4.0,
            "length_m": 10.0,
            "area_m2": 40.0,
            "thickness": "30 Micras",
        },
        package_size="bobina 4×10 m (40 m²)",
        displayed=29.9,
        normalized=0.75,
        unit="m²",
        url="https://www.leroymerlin.com.br/bobina-de-lona-plastica-4x10m-preta-plasitap_92450225",
        verification=(
            "api/v3/products/92450225 HTTP 200 X-Region=campinas; pricing.price.to R$29,90; "
            "characteristics Largura=4,00 m and Comprimento=10,00 m → 40 m²; "
            "isAvailableOnEcommerce=true. Arithmetic: 29.90 / 40 = 0.7475 → R$0.75/m²."
        ),
        caveats=[
            "Lowest verified in-stock per-m² among priced available plastic tarps.",
            "Freight for CEP 13380-000 not calculated.",
        ],
    ),
    cand(
        name="Lona Plástica 4x50m Preta BRF Lonas",
        sku=88036865,
        brand="BRF Lonas",
        specs={
            "brand": "BRF Lonas",
            "color": "Preto",
            "nominal_size": "4x50 m",
            "area_m2_nominal": 200.0,
        },
        package_size="rolo 4×50 m (200 m² nominal)",
        displayed=149.9,
        normalized=0.75,
        unit="m²",
        url="https://www.leroymerlin.com.br/lona-plastica-4x50m-preta-brf-lonas_88036865",
        verification=(
            "api/v3/products/88036865 HTTP 200 X-Region=campinas; pricing.price.to R$149,90; "
            "product name 4x50m; isAvailableOnEcommerce=true. "
            "Arithmetic: 149.90 / 200 = 0.7495 → R$0.75/m²."
        ),
        caveats=[
            "Normalized from product-name 4×50 m; API characteristic dimensions were inconsistent.",
        ],
    ),
]


def expense(eid, item, unit, candidates, no_match_reason=None):
    if not candidates:
        return {
            "expense_id": eid,
            "requested_item": item,
            "requested_unit": unit,
            "match_status": "no_match",
            "candidates": [],
            "winner": None,
            "no_match_reason": no_match_reason
            or "No comparable product with visible price verified on a direct leroymerlin.com.br product page for this unit.",
        }
    ranked = sorted(candidates, key=lambda c: c["normalized_unit_price_brl"])
    return {
        "expense_id": eid,
        "requested_item": item,
        "requested_unit": unit,
        "match_status": "verified",
        "candidates": ranked,
        "winner": ranked[0],
        "no_match_reason": None,
    }


payload = {
    "cluster": "finishes",
    "checked_at": CHECKED,
    "location_basis": LOC,
    "expenses": [
        expense("EXP_0023", "Porcelanato", "m²", c23),
        expense("EXP_0024", "Rejunte de porcelanato", "kg", c24),
        expense("EXP_0025", "Argamassa para o porcelanato", "saco (20 kg)", c25),
        expense(
            "EXP_0041",
            "Rodapés",
            "metro linear (m)",
            [],
            no_match_reason=(
                "Rodapé SKUs found (e.g. PVC/poliestireno 1571598281, 1572343516) but "
                "api/v3/products returned no pricing.price.to and/or isAvailableOnEcommerce=false; "
                "no verifiable in-stock linear-metre price on a direct /<slug>_<id> offer."
            ),
        ),
        expense("EXP_0046", "Tinta", "lata (18 L)", c46),
        expense(
            "EXP_0048",
            "Silicone, espuma expansiva, selante PU",
            "kit",
            [c48_kit, sil, esp],
        ),
        expense("EXP_0049", "Lona para proteção", "m²", c49),
    ],
}

# Fix EXP_0048 ranking: kit should win by kit unit; component candidates have lower unit prices
# Re-order manually so kit is winner for the expense
payload["expenses"][5]["candidates"] = [c48_kit, sil, esp]
payload["expenses"][5]["winner"] = c48_kit

OUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
verified = sum(1 for e in payload["expenses"] if e["match_status"] == "verified")
no_match = sum(1 for e in payload["expenses"] if e["match_status"] == "no_match")
print(f"Wrote {OUT}")
print(f"verified={verified} no_match={no_match}")
for e in payload["expenses"]:
    w = e.get("winner") or {}
    print(
        e["expense_id"],
        e["match_status"],
        w.get("normalized_unit_price_brl"),
        (w.get("matched_product") or e.get("no_match_reason", ""))[:70],
    )
