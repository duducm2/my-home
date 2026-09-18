"""Single-expense verbose debug."""
from urllib.parse import quote
from playwright.sync_api import sync_playwright
import re

PRICE_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")
BASE = "https://www.leroymerlin.com.br"
query = "cimento 50kg"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    )
    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    search_url = f"{BASE}/search?term={quote(query)}&searchTerm={quote(query)}&searchType=default"
    resp = page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
    print("search status", resp.status if resp else None)
    page.wait_for_timeout(3000)
    raw = page.evaluate(
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
        out.push({ name, sku, url, block: block.slice(0, 200) });
      }
      return out;
    }"""
    )
    print("raw count", len(raw))
    for item in raw[:5]:
        print("ITEM", item)
        prices = PRICE_RE.findall((item.get("block") or "").replace("\xa0", " "))
        print("  prices", prices)
    if raw:
        url = raw[0]["url"]
        resp2 = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        print("pdp status", resp2.status if resp2 else None, page.url)
        body = page.inner_text("body")[:1500]
        print("pdp prices", PRICE_RE.findall(body.replace("\xa0", " "))[:5])
        print("h1", page.locator("h1").inner_text() if page.locator("h1").count() else None)
    browser.close()
