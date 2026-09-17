"""Assign practical measurement units to the repository's seeded expenses."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path


UNITS = {
    "EXP_0001": "pagamento",
    "EXP_0002": "imposto",
    "EXP_0003": "serviço",
    "EXP_0004": "registro",
    "EXP_0005": "serviço",
    "EXP_0006": "pacote de ligações",
    "EXP_0007": "reserva",
    "EXP_0008": "tarifa",
    "EXP_0009": "multa",
    "EXP_0010": "serviço",
    "EXP_0011": "parcela",
    "EXP_0012": "mês",
    "EXP_0013": "contrato",
    "EXP_0014": "balde",
    "EXP_0015": "metro cúbico (m³)",
    "EXP_0016": "saco (50 kg)",
    "EXP_0017": "unidade",
    "EXP_0018": "conjunto",
    "EXP_0019": "unidade",
    "EXP_0020": "unidade",
    "EXP_0021": "quilograma (kg)",
    "EXP_0022": "caçamba",
    "EXP_0023": "metro quadrado (m²)",
    "EXP_0024": "quilograma (kg)",
    "EXP_0025": "saco (20 kg)",
    "EXP_0026": "unidade",
    "EXP_0027": "unidade",
    "EXP_0028": "unidade",
    "EXP_0029": "unidade",
    "EXP_0030": "unidade",
    "EXP_0031": "unidade",
    "EXP_0032": "serviço",
    "EXP_0033": "unidade",
    "EXP_0034": "metro linear (m)",
    "EXP_0035": "unidade",
    "EXP_0036": "unidade",
    "EXP_0037": "unidade",
    "EXP_0038": "unidade",
    "EXP_0039": "conjunto",
    "EXP_0040": "unidade",
    "EXP_0041": "metro linear (m)",
    "EXP_0042": "metro quadrado (m²)",
    "EXP_0043": "metro linear (m)",
    "EXP_0044": "unidade",
    "EXP_0045": "conjunto",
    "EXP_0046": "lata (18 L)",
    "EXP_0047": "pacote",
    "EXP_0048": "kit",
    "EXP_0049": "metro quadrado (m²)",
}


def replace(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="")
    os.replace(temporary, path)


def assign(data_dir: Path) -> None:
    expense_path = data_dir / "expenses.csv"
    with expense_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        expenses = list(reader)

    expense_ids = {row["id"] for row in expenses}
    if expense_ids != set(UNITS):
        missing = sorted(expense_ids - set(UNITS))
        stale = sorted(set(UNITS) - expense_ids)
        raise ValueError(f"unit map mismatch; missing={missing}, stale={stale}")

    for expense in expenses:
        expense["unit"] = UNITS[expense["id"]]

    temporary = expense_path.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(expenses)
    os.replace(temporary, expense_path)

    quotation_path = data_dir / "quotations.json"
    document = json.loads(quotation_path.read_text(encoding="utf-8-sig"))
    for quotation in document.get("quotations", []):
        expense_id = str(quotation.get("expense_id") or "")
        if expense_id not in UNITS:
            continue
        quotation["unit"] = UNITS[expense_id]
        metadata = quotation.setdefault("metadata", {})
        metadata["measurement_unit_source"] = "semantic review 2026-09-16"
        metadata["measurement_unit_inferred"] = True
    replace(
        quotation_path,
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
    )


if __name__ == "__main__":
    assign(Path(__file__).resolve().parents[1] / "data")
