import re
import html as H
from pathlib import Path
from urllib.parse import unquote

raw = Path(r"C:/Users/eduev/AppData/Local/Temp/bing.html").read_text(
    encoding="utf-8", errors="ignore"
)
print("CITES:")
for c in re.findall(r"<cite[^>]*>(.*?)</cite>", raw):
    t = re.sub("<[^>]+>", "", c)
    print(H.unescape(t))
print("---H2---")
for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", raw, re.S):
    t = re.sub("<[^>]+>", "", m.group(1))
    t = H.unescape(re.sub(r"\s+", " ", t)).strip()
    if t:
        print(t[:200])
print("---decoded u=---")
for m in re.finditer(r"u=%2f[^&\"]+", raw):
    s = unquote(m.group(0))
    if "leroymerlin" in s.lower():
        print(s[:250])
print("---product paths---")
for m in re.findall(r"leroymerlin\.com\.br/[a-zA-Z0-9\-_%]+_\d+", raw):
    print(unquote(m))
