"""Debug Leroy Merlin playwright extraction."""
from playwright.sync_api import sync_playwright
from urllib.parse import quote

BASE = "https://www.leroymerlin.com.br"
query = "cimento 50kg"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        locale="pt-BR",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    url = f"{BASE}/search?term={quote(query)}&searchTerm={quote(query)}&searchType=default"
    resp = page.goto(url, wait_until="networkidle", timeout=90000)
    print("status", resp.status if resp else None, "final", page.url)
    print("title", page.title())
    page.wait_for_timeout(3000)
    info = page.evaluate(
        """() => {
      const anchors = [...document.querySelectorAll('a[href]')];
      const productish = anchors.filter(a => /_\\d{5,}/.test(a.pathname)).map(a => a.href).slice(0, 10);
      const textHasPrice = (document.body?.innerText || '').includes('R$');
      const bodyLen = (document.body?.innerText || '').length;
      const sample = (document.body?.innerText || '').slice(0, 800);
      return {productish, textHasPrice, bodyLen, sample, anchorCount: anchors.length};
    }"""
    )
    print(info)
    # try headed-like wait for product heading
    try:
        page.wait_for_selector("text=Cimento", timeout=10000)
        print("found Cimento text")
    except Exception as e:
        print("wait Cimento failed", e)
    browser.close()
