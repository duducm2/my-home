"""Build LM product URL candidates from Bing CDN image IDs and known redirects."""
from __future__ import annotations

import base64
import re
from pathlib import Path
from urllib.parse import unquote

# Decoded from Bing ck redirects + CDN product image filenames
candidates = {
    "EXP_0024": [
        # slug_id guessed from CDN: products/<slug_underscores>_<id>_<hash>
        ("rejunte-acrilico-branco-1-kg-quartzolit_91931840", "Rejunte Acrílico Branco 1 Kg Quartzolit"),
        ("rejunte-acrilico-corda-1-kg-quartzolit_91931875", "Rejunte Acrílico Corda 1 Kg Quartzolit"),
        ("rejunte-acrilico-marfim-1kg-portobello_92367394", "Rejunte Acrílico Marfim 1kg Portobello"),
        ("rejunte-acrilico-camurca-1kg-fortaleza_92380953", "Rejunte Acrílico Camurça 1kg Fortaleza"),
        ("rejunte-acrilico-fortaleza-1kg-chocolate_1570939729", "Rejunte Acrílico Fortaleza 1kg Chocolate"),
        ("rejunte-acrilico-rejunte-base-plastica-cinza-platina-1kg-axton_92108380", "Rejunte Acrílico Cinza Platina 1kg Axton"),
        ("rejunte-acrilico-rejunte-base-plastica-areia-1kg-axton_92108611", "Rejunte Acrílico Areia 1kg Axton"),
        ("rejunte-para-areas-umidas-acrilico-marfim-1kg-axton_90537251", "Rejunte Acrílico Premium Marfim 1 Kg Axton"),
        ("rejunte-acrilico-1kg-cafe-fortaleza_1571039551", "Rejunte Acrílico 1kg Café Fortaleza"),
        ("rejunte-acrilico-quartzobras-1kg-terracota_1571980463", "Rejunte Acrílico Quartzobrás 1kg Terracota"),
        ("rejunte-acrilico-bicomponente-ceramfix-1kg-creme_603885", "Rejunte Acrilico Bicomponente Ceramfix 1kg Creme"),
        ("rejunte-acrilico-bicomponente-extraliso-branco-ceramfix-1kg_1571039535", "Rejunte Acrilico Bicomponente Extraliso Branco Ceramfix"),
    ],
    "EXP_0025": [
        ("argamassa-aciii-interno-e-externo-20kg-cinza-votomassa-votorantim_87125962", "Argamassa ACIII Cinza Votomassa 20kg"),
        ("argamassa-aciii-interno-e-externo-20kg-branco-votomassa-votorantim_87912153", "Argamassa ACIII Branco Votomassa 20kg"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-cimentcola-flexivel-quartzolit_89684140", "Argamassa ACIII Cinza Cimentcola Flexível Quartzolit"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-axton_89296172", "Argamassa ACIII Cinza Axton 20kg"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-mg-massa_92524775", "Argamassa ACIII Cinza Mg Massa 20kg"),
        ("argamassa-aciii-interno-e-externo-20kg-branco-cimentcola-quartzolit_90985930", "Argamassa ACIII Branco CimentCola Quartzolit"),
        ("argamassa-aciii-interno-e-externo-20kg-ultra-flexivel-m29-hp-cinza-mc-bauchemie_92394743", "Argamassa ACIII Ultra Flexível M29 HP"),
        ("argamassa-aciii-interno-e-externo-20kg-cinza-br-massa_89229791", "Argamassa ACIII Cinza BR Massa 20kg"),
        ("argamassa-colante-aciii-20-kg_92322503", "Argamassa Colante ACIII Ciplan 20kg"),
        ("argamassa-colante-aciii-porcelanato-20kg_92173144", "Argamassa Colante ACIII Porcelanato MassaForte"),
        ("argamassa-aciii-flex-interno-e-externo-cinza-20kg-argalit_90609092", "Argamassa ACIII Argalit 20kg"),
        ("argamassa-aciii-interno-e-externo-cinza-20kg-axton_89820234", "Argamassa ACIII Axton CDN alt"),
        ("argamassa-aciii-branca-20kg-quartzrevest_92453333", "Argamassa ACIII Branca Quartz Revest"),
        ("argamassa-aciii-premium-interno-e-externo-cinza-20kg-argalit_90609106", "Argamassa ACIII Premium Argalit"),
        ("argamassa-flex-aciii-interno-e-externo-cinza-20kg-fortaleza_90220144", "Argamassa Flex ACIII Fortaleza"),
        ("argamassa-aciii-interno-e-externo-cinza-20kg_85526182", "Argamassa ACIII Cinza generic"),
        ("argamassa-colante-aciii-cinza-20kg-precon_86857680", "Argamassa ACIII Precon"),
        ("argamassa-aciii-interno-e-externo-20kg-ultra-flexivel-m29-hp_92394750", "Argamassa Ultra Flex M29 HP Branco"),
        ("argamassa-aciii-interno-e-externo-20kg-ultra-flexivel-m12-hp_92394736", "Argamassa Ultra Flex M12 HP"),
        ("argamassa-colante-aciii-saco-de-20kg-br-massa_89229791", "Argamassa Colante BR Massa CDN"),
    ],
}

# Also decode a few known Bing base64 payloads to confirm
samples = [
    "aHR0cHM6Ly93d3cubGVyb3ltZXJsaW4uY29tLmJyL2FyZ2FtYXNzYS1hY2lpaS1pbnRlcm5vLWUtZXh0ZXJuby0yMGtnLWNpbnphLXZvdG9tYXNzYS12b3RvcmFudGltXzg3MTI1OTYy",
    "aHR0cHM6Ly93d3cubGVyb3ltZXJsaW4uY29tLmJyL2FyZ2FtYXNzYS1hY2lpaS1pbnRlcm5vLWUtZXh0ZXJuby0yMGtnLWNpbnphLWF4dG9uXzg5Mjk2MTcy",
]
print("Decoded samples:")
for s in samples:
    print(" ", base64.b64decode(s + "==").decode())

out = Path(r"C:\Users\eduev\Meu Drive\17 - Projects\my-home\data\research\leroymerlin\_tmp_finishes_urls.txt")
lines = []
for exp, items in candidates.items():
    for slug, name in items:
        url = f"https://www.leroymerlin.com.br/{slug}"
        lines.append(f"{exp}\t{url}\t{name}")
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {len(lines)} URLs to {out}")
