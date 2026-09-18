"""Debug search HTML and try alternate engines."""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
OUT = Path(__file__).with_name("_tmp_search_debug")
OUT.mkdir(exist_ok=True)

QUERIES = [
    "leroymerlin.com.br quadro de distribuicao embutir",
    "leroymerlin quadro distribuicao preço",
    '"leroymerlin.com.br" eletroduto corrugado',
    "leroymerlin lampada led bulbo",
    "leroymerlin tomada 2P+T",
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as resp:
        return resp.read()


def main() -> None:
    engines = {
        "bing": lambda q: "https://www.bing.com/search?q=" + urllib.parse.quote(q),
        "ddg": lambda q: "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q),
        "brave": lambda q: "https://search.brave.com/search?q=" + urllib.parse.quote(q),
        "yandex": lambda q: "https://yandex.com/search/?text=" + urllib.parse.quote(q),
    }
    prod = re.compile(rb"leroymerlin\.com\.br/[a-z0-9\-]+_\d+", re.I)
    for q in QUERIES:
        for name, build in engines.items():
            url = build(q)
            try:
                raw = fetch(url)
            except Exception as exc:
                print("ERR", name, q, exc)
                continue
            path = OUT / f"{name}_{re.sub(r'[^a-z0-9]+', '_', q.lower())[:50]}.html"
            path.write_bytes(raw)
            matches = prod.findall(raw)
            print(name, q[:40], "bytes", len(raw), "matches", len(matches), "file", path.name)
            for m in matches[:5]:
                print(" ", m.decode())
            # show if captcha/block
            low = raw.lower()
            flags = []
            for token in (b"captcha", b"unusual traffic", b"datadome", b"challenge", b"bot"):
                if token in low:
                    flags.append(token.decode())
            if flags:
                print("  flags:", flags)


if __name__ == "__main__":
    main()
