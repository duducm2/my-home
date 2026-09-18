"""Seed expense_allocations on micro-activities from curated task→expense maps."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from persistence import atomic_write_text

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TASKS_PATH = DATA / "tasks.json"
EXPENSES_PATH = DATA / "expenses.csv"

# Primary task owns full default_expected_quantity for that expense.
# Format: task_id -> [expense_id, ...]
TASK_EXPENSES: dict[str, list[str]] = {
    # Compra e financiamento
    "TASK_0001": ["EXP_0001"],  # Entrada
    "TASK_0002": ["EXP_0002", "EXP_0003"],  # ITBI + cartório
    "TASK_0004": ["EXP_0008"],  # Taxa Caixa
    "TASK_0005": ["EXP_0004"],  # Registro financiamento
    "TASK_0006": ["EXP_0011"],  # Parcela financiamento
    "TASK_0008": ["EXP_0005", "EXP_0009"],  # Mudança + multa aluguel
    "TASK_0098": ["EXP_0003"],  # Matrícula / cartório (shared note)
    # Regularização e preparação
    "TASK_0011": ["EXP_0022", "EXP_0020"],  # Demolição: caçamba + carrinho
    "TASK_0081": ["EXP_0022"],
    "TASK_0016": ["EXP_0024"],  # Rejuntes
    "TASK_0017": ["EXP_0014", "EXP_0015", "EXP_0016"],  # Bianco + areia + cimento
    "TASK_0012": ["EXP_0014"],
    "TASK_0014": ["EXP_0014"],
    "TASK_0015": ["EXP_0014"],
    "TASK_0020": ["EXP_0017"],  # Telhas
    "TASK_0083": ["EXP_0017"],
    "TASK_0021": ["EXP_0042", "EXP_0043"],  # Madeiramento / calhas
    "TASK_0084": ["EXP_0042"],
    "TASK_0027": ["EXP_0032"],  # Eletricista
    "TASK_0029": ["EXP_0033"],  # Quadro
    "TASK_0034": ["EXP_0034"],  # Conduítes
    "TASK_0035": ["EXP_0038"],  # Tomadas
    "TASK_0036": ["EXP_0038"],
    "TASK_0095": ["EXP_0034", "EXP_0038"],
    "TASK_0018": ["EXP_0015", "EXP_0016"],
    "TASK_0082": ["EXP_0015"],
    "TASK_0026": ["EXP_0019", "EXP_0021"],  # Tijolo + arame
    # Reforma e melhorias
    "TASK_0038": ["EXP_0044"],  # Caixa d'água / água
    "TASK_0039": ["EXP_0037"],  # Esgoto / ralos
    "TASK_0040": ["EXP_0036"],  # Torneiras / chuveiro
    "TASK_0042": ["EXP_0028"],  # Vaso
    "TASK_0043": ["EXP_0037"],
    "TASK_0045": ["EXP_0014"],  # Impermeabilização
    "TASK_0052": ["EXP_0014"],
    "TASK_0046": ["EXP_0031"],  # Janela / vitrô banheiro area
    "TASK_0047": ["EXP_0030"],  # Vitrô
    "TASK_0053": ["EXP_0023", "EXP_0024", "EXP_0025"],  # Porcelanato kit
    "TASK_0087": ["EXP_0023", "EXP_0024", "EXP_0025", "EXP_0041"],
    "TASK_0054": ["EXP_0023"],
    "TASK_0056": ["EXP_0026", "EXP_0029"],  # Portas e janelas
    "TASK_0057": ["EXP_0027"],  # Porta-balcão
    "TASK_0091": ["EXP_0027"],
    "TASK_0092": ["EXP_0029"],  # 5 janelas
    "TASK_0093": ["EXP_0026"],  # 5 portas
    "TASK_0090": ["EXP_0028", "EXP_0039", "EXP_0040", "EXP_0031"],  # Banheiro
    "TASK_0089": ["EXP_0026", "EXP_0039", "EXP_0040"],  # Suíte
    "TASK_0058": ["EXP_0036", "EXP_0039"],
    "TASK_0062": ["EXP_0037"],
    "TASK_0063": ["EXP_0038"],
    "TASK_0065": ["EXP_0032", "EXP_0035"],
    "TASK_0096": ["EXP_0045"],  # Segurança muros
    "TASK_0088": ["EXP_0013", "EXP_0019", "EXP_0049"],  # Gourmet / pedreiro
    # Pintura e acabamentos
    "TASK_0068": ["EXP_0046"],  # Tinta interna
    "TASK_0069": ["EXP_0046"],
    "TASK_0070": ["EXP_0041"],  # Rodapés
    "TASK_0071": ["EXP_0047", "EXP_0048"],  # Arremates
    "TASK_0072": ["EXP_0048"],
    "TASK_0073": ["EXP_0036", "EXP_0028"],  # Louças/metais
    "TASK_0074": ["EXP_0035"],  # Iluminação
    "TASK_0075": ["EXP_0047"],
    # Mudança
    "TASK_0076": ["EXP_0049"],
    "TASK_0077": ["EXP_0005"],
    "TASK_0010": [],  # macro — skipped
}


def load_quantities() -> dict[str, float]:
    quantities: dict[str, float] = {}
    with EXPENSES_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                quantities[row["id"]] = float(row["default_expected_quantity"] or 1)
            except ValueError:
                quantities[row["id"]] = 1.0
    return quantities


def main() -> int:
    quantities = load_quantities()
    document = json.loads(TASKS_PATH.read_text(encoding="utf-8-sig"))
    tasks = document.get("tasks") or []
    updated = 0
    linked_expenses: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict) or task.get("activity_type") != "task":
            continue
        task_id = str(task.get("id") or "")
        expense_ids = TASK_EXPENSES.get(task_id)
        if expense_ids is None:
            continue
        # Deduplicate expense ids while preserving order
        seen: set[str] = set()
        allocations = []
        for expense_id in expense_ids:
            if expense_id in seen or expense_id not in quantities:
                continue
            seen.add(expense_id)
            linked_expenses.add(expense_id)
            allocations.append(
                {
                    "expense_id": expense_id,
                    "expected_quantity": quantities[expense_id],
                }
            )
        previous = task.get("expense_allocations") or []
        if previous != allocations:
            task["expense_allocations"] = allocations
            updated += 1
    atomic_write_text(
        TASKS_PATH,
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
    )
    print(
        f"Updated {updated} tasks; "
        f"{len(linked_expenses)} distinct expenses linked; "
        f"mapped keys {len(TASK_EXPENSES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
