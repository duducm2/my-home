"""Search engines for tools/logistics LM product URLs."""
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
    "carrinho de mão site:leroymerlin.com.br",
    "carrinho de mao tramontina site:leroymerlin.com.br",
    "kit ferramentas tramontina site:leroymerlin.com.br",
    "jogo de ferramentas site:leroymerlin.com.br",
    "calha galvanizada site:leroymerlin.com.br",
    "rufo galvanizado site:leroymerlin.com.br",
    "kit parafuso bucha site:leroymerlin.com.br",
    "prego 17x21 site:leroymerlin.com.br",
    "caçamba entulho site:leroymerlin.com.br",
]

ENGINES = {
    "bing": lambda q: "https://www.bing.com/search?q=" + urllib.parse.quote(q) + "&count=30",
    "brave": lambda q: "https://search.brave.com/search?q=" + urllib.parse.quote(q),
    "yandex": lambda q: "https://yandex.com/search/?text=" + urllib.parse.quote(q),
}

PROD = re.compile(r"leroymerlin\.com\.br/[a-z0-9\-_%]+_\d+", re.I)


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
    for q in QUERIES:
        for name, build in ENGINES.items():
            url = build(q)
            slug = re.sub(r"[^a-z0-9]+", "_", q.lower())[:45]
            path = OUT / f"tools_{name}_{slug}.html"
            try:
                raw = fetch(url)
            except Exception as exc:
                print("ERR", name, q[:40], type(exc).__name__, exc)
                continue
            path.write_bytes(raw)
            text = raw.decode("utf-8", "replace")
            matches = list(dict.fromkeys(PROD.findall(text)))
            print(name, q[:45], "bytes", len(raw), "matches", len(matches))
            for m in matches[:8]:
                print(" ", urllib.parse.unquote(m))
            low = raw.lower()
            flags = [t.decode() for t in (b"captcha", b"datadome", b"challenge") if t in low]
            if flags:
                print("  flags:", flags)


if __name__ == "__main__":
    main()
