from pathlib import Path

html = Path("web/index.html").read_text(encoding="utf-8")
js = Path("web/app.js").read_text(encoding="utf-8")
start = html.find('id="view-expenses"')
end = html.find('id="view-contracts"')
chunk = html[start:end]
assert "Preço por unidade" in chunk
assert "Planejado" not in chunk
assert "Cenários e preço" not in chunk
assert "quotation-action-btn" not in chunk
assert "quotation-bento" in html
assert "expense-allocation-usage" in html
assert "function unitPriceCell" in js
assert "function renderQuotationBento" in js
assert "function quotationEvidenceItems" in js
assert 'setQuotationTab("responses")' in js
snippet = js[
    js.find("function allocationCost") : js.find("function allocationCost") + 400
]
assert "shipping_cost" in snippet
print("verification ok")
