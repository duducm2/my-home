import urllib.request
import urllib.parse
import re

ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
queries = [
    "cimento 50kg",
    "areia metro cubico",
    "telha portuguesa ceramica",
    "tijolinho barro",
    "arame recozido",
    "estrutura metalica",
    "telha metalica",
    "pedrisco",
]
for q in queries:
    url = "https://www.sodimac.com.br/sodimac-br/search/?Ntt=" + urllib.parse.quote(q)
    try:
        req = urllib.request.Request(url, headers=ua)
        html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
        links = re.findall(r'href="(/sodimac-br/product/[^"]+)"', html)
        uniq = []
        for l in links:
            if l not in uniq:
                uniq.append(l)
        print("===", q, "links", len(uniq))
        for l in uniq[:10]:
            print(l)
        titles = re.findall(r'"displayName"\s*:\s*"([^"]+)"', html)
        prices = re.findall(r'"price"\s*:\s*([0-9.]+)', html)
        print("names", titles[:5], "prices", prices[:5])
    except Exception as e:
        print("===", q, "ERR", e)
