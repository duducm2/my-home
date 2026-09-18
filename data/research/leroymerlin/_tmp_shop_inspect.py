"""Inspect Bing shop embedded JSON for rodapé offers."""
from __future__ import annotations

import re
import ssl
import urllib.parse
import urllib.request

ctx = ssl.create_default_context()
url = "https://www.bing.com/shop?q=" + urllib.parse.quote(
    "rodape poliestireno leroymerlin"
)
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=40, context=ctx).read().decode(
    "utf-8", "replace"
)

for m in re.finditer(r"<script[^>]*>(.*?)</script>", html, re.S | re.I):
    s = m.group(1)
    if "Leroy" not in s and "rodap" not in s.lower() and "offerId" not in s:
        continue
    if len(s) < 200:
        continue
    print("SCRIPT len", len(s))
    urls = re.findall(r"https?://[^\"\\s<>]+leroymerlin[^\"\\s<>]+", s)
    print(" urls", urls[:10])
    titles = re.findall(r'"title":"([^"]{5,120})"', s)
    print(" titles", titles[:20])
    prices = re.findall(r'"price":([0-9.]+)', s)
    print(" prices", prices[:20])
    i = s.find("Leroy")
    if i > 0:
        print(" context", s[max(0, i - 250) : i + 450])
    print("---")
