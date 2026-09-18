"""Debug with system Chrome channel."""
from playwright.sync_api import sync_playwright
from urllib.parse import quote

BASE = "https://www.leroymerlin.com.br"
query = "cimento 50kg"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
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
    resp = page.goto(url, wait_until="domcontentloaded", timeout=90000)
    print("status", resp.status if resp else None, "final", page.url)
    page.wait_for_timeout(4000)
    info = page.evaluate(
        """() => ({
      title: document.title,
      bodyLen: (document.body?.innerText || '').length,
      productish: [...document.querySelectorAll('a[href]')].filter(a => /_\\d{5,}/.test(a.pathname)).map(a => a.href).slice(0, 8),
      sample: (document.body?.innerText || '').slice(0, 500)
    })"""
    )
    print(info)
    browser.close()
