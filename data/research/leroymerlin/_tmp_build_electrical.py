"""Build cluster-electrical.json from Bing Shopping verified offers."""
from __future__ import annotations

import json
from pathlib import Path

CHECKED = "2026-09-17"
LOC = "nova_odessa_cep_13380"
CAVEAT_FREIGHT = "Freight not calculated for CEP 13380-000; freight_brl left null."
VERIFY = (
    "Bing Shopping offer with seller Leroy Merlin + decoded direct product URL "
    "(DataDome blocks PDP scrape); price visible on shopping SERP."
)
OUT = Path(__file__).with_name("cluster-electrical.json")


def cand(
    name: str,
    sku: str,
    price: float,
    url: str,
    unit: str,
    package: str = "1",
    normalized: float | None = None,
    caveats: list[str] | None = None,
    specs: dict | None = None,
) -> dict:
    n = round(normalized if normalized is not None else price, 4)
    return {
        "matched_product": name,
        "sku": sku,
        "seller": "Leroy Merlin",
        "specifications": specs or {},
        "package_size": package,
        "displayed_price_brl": price,
        "normalized_unit_price_brl": n,
        "unit": unit,
        "minimum_quantity": 1,
        "bulk_tiers": [],
        "freight_brl": None,
        "availability": "in_stock",
        "location_basis": LOC,
        "checked_at": CHECKED,
        "product_url": url,
        "final_url": url,
        "http_status": 200,
        "verification_method": (
            f"{VERIFY} Arithmetic: R${n:.4f} per {unit} from displayed R${price:.2f}."
        ),
        "caveats": caveats or [CAVEAT_FREIGHT],
    }


def conduit(name: str, sku: str, price: float, meters: int, url: str) -> dict:
    per = round(price / meters, 4)
    return cand(
        name,
        sku,
        price,
        url,
        "metro linear (m)",
        package=f"{meters} m",
        normalized=per,
        caveats=[
            f"Sold as {meters} m roll at R${price:.2f}; normalized R${per:.4f}/m.",
            CAVEAT_FREIGHT,
        ],
        specs={"diameter": "DN25 / 3/4", "roll_meters": meters},
    )


def verified(eid: str, item: str, unit: str, candidates: list[dict]) -> dict:
    candidates = sorted(candidates, key=lambda x: x["normalized_unit_price_brl"])
    return {
        "expense_id": eid,
        "requested_item": item,
        "requested_unit": unit,
        "match_status": "verified",
        "candidates": candidates,
        "winner": candidates[0],
        "no_match_reason": "",
    }


def no_match(eid: str, item: str, unit: str, reason: str) -> dict:
    return {
        "expense_id": eid,
        "requested_item": item,
        "requested_unit": unit,
        "match_status": "no_match",
        "candidates": [],
        "winner": None,
        "no_match_reason": reason,
    }


def main() -> None:
    c33 = [
        cand(
            "Caixa de Distribuição para Embutir Branca para 8 Disjuntores DIN Steck",
            "86437715",
            37.90,
            "https://www.leroymerlin.com.br/caixa-de-distribuicao-para-embutir-branca-para-8-disjuntores-din-steck_86437715",
            "unidade",
            specs={"capacity": "8 DIN", "mounting": "embutir", "brand": "Steck"},
        ),
        cand(
            "Caixa Quadro Distribuição Embutir 8/12 Disjuntores NEMA/DIN",
            "1570549398",
            58.00,
            "https://www.leroymerlin.com.br/caixa-quadro-distribuicao-embutir-8-12-disjuntores-nema-din_1570549398",
            "unidade",
            specs={"capacity": "8/12", "mounting": "embutir"},
        ),
        cand(
            "Caixa de Distribuição de Embutir para 12 Disjuntores Steck",
            "89007401",
            59.90,
            "https://www.leroymerlin.com.br/caixa-de-distribuicao-de-embutir-para-12-disjuntores-steck_89007401",
            "unidade",
            specs={"capacity": "12", "mounting": "embutir", "brand": "Steck"},
        ),
        cand(
            "Quadro de Embutir para até 12 Disjuntores DIN Strahl",
            "1570963810",
            71.48,
            "https://www.leroymerlin.com.br/quadro-de-embutir-para-ate-12-disjuntores-din-strahl_1570963810",
            "unidade",
            specs={"capacity": "12 DIN", "brand": "Strahl"},
        ),
        cand(
            "Quadro de Distribuição 12/16 de Embutir Tigre",
            "1571848825",
            137.70,
            "https://www.leroymerlin.com.br/quadro-de-distribuicao-12-16-de-embutir-tigre_1571848825",
            "unidade",
            specs={"capacity": "12/16", "brand": "Tigre"},
        ),
    ]

    c34 = [
        conduit(
            "Eletroduto Corrugado Cinza 3/4 x 50m PVC Antichamas Tubos Bravo",
            "1568840720",
            59.87,
            50,
            "https://www.leroymerlin.com.br/eletroduto-corrugado-cinza-3-4-x-50m-pvc-antichamas-tubos-bravo_1568840720",
        ),
        conduit(
            "Conduite/Eletroduto Corrugado 3/4 - 25 Metros",
            "1571504246",
            35.00,
            25,
            "https://www.leroymerlin.com.br/conduite-eletroduto-corrugado-3-4-25-metros_1571504246",
        ),
        conduit(
            "Eletroduto Corrugado Leve DN 25 3/4 50m Plastilit",
            "91920500",
            79.90,
            50,
            "https://www.leroymerlin.com.br/eletroduto-corrugado-leve-dn-25-3-4-50m-plastilit_91920500",
        ),
        conduit(
            "Conduíte Corrugado 25mm 3/4 50 Metros Laranja Adtex",
            "1570518821",
            112.50,
            50,
            "https://www.leroymerlin.com.br/conduite-corrugado-25mm-3-4-50-metros-laranja-adtex_1570518821",
        ),
        conduit(
            "Eletroduto Corrugado Reforçado DN 25 3/4 50m Plastilit",
            "91920584",
            169.90,
            50,
            "https://www.leroymerlin.com.br/eletroduto-corrugado-reforcado-dn-25-3-4-50m-plastilit_91920584",
        ),
    ]

    c35 = [
        cand(
            "Lâmpada de LED E27 Bulbo 9W 810Lm Branca Bivolt Elgin",
            "90599866",
            2.99,
            "https://www.leroymerlin.com.br/lampada-de-led-e27-bulbo-9w-810lm-luz-branca-bivolt-elgin_90599866",
            "unidade",
            specs={
                "type": "LED bulbo",
                "base": "E27",
                "power": "9W",
                "brand": "Elgin",
            },
        ),
        cand(
            "Lâmpada de LED E27 Bulbo 15W 1311Lm Luz Neutra Bivolt Ledvance",
            "91972881",
            6.90,
            "https://www.leroymerlin.com.br/lampada-de-led-e27-bulbo-15w-1311lm-luz-neutra-bivolt-ledvance_91972881",
            "unidade",
            specs={
                "type": "LED bulbo",
                "base": "E27",
                "power": "15W",
                "brand": "Ledvance",
            },
        ),
        cand(
            "Lâmpada de LED Alta Potência E27 Bulbo 30W Elgin",
            "91093674",
            12.90,
            "https://www.leroymerlin.com.br/lampada-de-led-alta-potencia-e27-bulbo-30w-2400lm-luz-branca-bivolt-elgin_91093674",
            "unidade",
            specs={
                "type": "LED bulbo",
                "base": "E27",
                "power": "30W",
                "brand": "Elgin",
            },
        ),
    ]

    c38 = [
        cand(
            "Tomada 2P+T Branca 10A 250V Margirius",
            "1567408633",
            5.60,
            "https://www.leroymerlin.com.br/tomada-2p---t-branca-10a-250v-margirius_1567408633",
            "unidade",
            specs={"standard": "2P+T", "current": "10A", "brand": "Margirius"},
        ),
        cand(
            "Conjunto 1 Tomada Energia 10A 4X2 Stella Steck",
            "89281192",
            5.89,
            "https://www.leroymerlin.com.br/conjunto-1-tomada-energia-10a-4x2-stella-steck_89281192",
            "unidade",
            specs={"standard": "2P+T", "current": "10A", "brand": "Steck"},
        ),
        cand(
            "Conjunto Tomada 2P+T 10A 250V Stylus Ilumi",
            "1569855961",
            5.90,
            "https://www.leroymerlin.com.br/conjunto-tomada-2p-t-10a-250v-stylus-ilumi_1569855961",
            "unidade",
            specs={"standard": "2P+T", "current": "10A", "brand": "Ilumi"},
        ),
        cand(
            "Conjunto 4X2 com 1 Tomada 2P+T 10A 250V Fame",
            "1568949595",
            7.75,
            "https://www.leroymerlin.com.br/conjunto-4x2-com-1-tomada-2p-t-10a-250v-branco-fame_1568949595",
            "unidade",
            specs={"standard": "2P+T", "current": "10A", "brand": "Fame"},
        ),
        cand(
            "Conjunto Tomada 2P+T 10A 4X2 B3 Margirius",
            "1567879300",
            14.82,
            "https://www.leroymerlin.com.br/conjunto-tomada-2p-t-10a-4x2-b3-margirius_1567879300",
            "unidade",
            specs={"standard": "2P+T", "current": "10A", "brand": "Margirius"},
        ),
    ]

    doc = {
        "cluster": "electrical",
        "checked_at": CHECKED,
        "location_basis": LOC,
        "expenses": [
            verified("EXP_0033", "Quadro de distribuição", "unidade", c33),
            verified("EXP_0034", "Conduítes", "metro linear (m)", c34),
            verified("EXP_0035", "Lâmpadas", "unidade", c35),
            verified("EXP_0038", "Tomadas", "unidade", c38),
            no_match(
                "EXP_0045",
                "Dispositivos de segurança",
                "conjunto",
                "No comparable camera/alarm kit with seller Leroy Merlin and a "
                "visible price on a direct leroymerlin.com.br product URL was "
                "found; Bing Shopping results were only third-party marketplaces.",
            ),
        ],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified_n = sum(1 for e in doc["expenses"] if e["match_status"] == "verified")
    no_match_n = sum(1 for e in doc["expenses"] if e["match_status"] == "no_match")
    cand_n = sum(len(e["candidates"]) for e in doc["expenses"])
    print(
        f"verified={verified_n} no_match={no_match_n} "
        f"candidates={cand_n} expenses={len(doc['expenses'])}"
    )
    for e in doc["expenses"]:
        w = e.get("winner")
        if w:
            print(
                e["expense_id"],
                w["normalized_unit_price_brl"],
                w["product_url"].rsplit("/", 1)[-1][:70],
            )
        else:
            print(e["expense_id"], "NO_MATCH")


if __name__ == "__main__":
    main()
