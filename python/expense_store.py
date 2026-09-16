"""CSV store for home expenses (CRUD + first-run seed)."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

HEADERS = [
    "id",
    "phase",
    "priority",
    "category",
    "description",
    "value",
    "created_at",
    "updated_at",
]

# (phase, priority, category, description, value)
SEED_ROWS: list[tuple[str, int, str, str, float]] = [
    ("Compra", 1, "Financiamento", "Entrada", 62000.00),
    ("Na formalização", 1, "Impostos", "ITBI — Nova Odessa (2%)", 6200.00),
    (
        "Na formalização",
        1,
        "Cartório",
        "Custos de cartório (Emolumentos de registro no Cartório de Registro de Imóveis; Taxas de certidão, autenticação e reconhecimento de firma)",
        1000.00,
    ),
    (
        "Na formalização",
        1,
        "Financiamento",
        "Registro do contrato de financiamento / alienação fiduciária",
        3300.00,
    ),
    ("Pós-mudança", 1, "Mudança", "Transporte / empresa de mudança", 700.00),
    (
        "Pós-mudança",
        1,
        "Instalação",
        "Taxas de ligação (água, esgoto, energia, gás, internet)",
        300.00,
    ),
    ("Primeiro ano", 1, "Reserva", "Reserva de emergência pós-compra", 4500.00),
    ("Pré-compra", 1, "Diligência", "Taxa de relacionamento da Caixa", 7000.00),
    ("Pré-compra", 1, "Diligência", "Multa do contrato de aluguel atual", 2400.00),
    ("Pré-compra", 1, "Diligência", "Reforma do apartamento atual", 1000.00),
    ("Pré-compra", 1, "Diligência", "Parcela do Financiamento", 2200.00),
    ("Pré-compra", 1, "Diligência", "Aluguel do imóvel atual", 1500.00),
    ("Manutenção", 1, "Mão de obra", "Pedreiro", 15000.00),
    ("Manutenção", 1, "Material", "Impermeabilizante (bianco)", 320.00),
    ("Manutenção", 1, "Material", "Areia grossa, fina e pedrisco", 700.00),
    ("Manutenção", 1, "Material", "Cimento", 650.00),
    ("Manutenção", 1, "Material", "Telha", 2000.00),
    ("Manutenção", 1, "Material", "Ferramentas", 1300.00),
    ("Manutenção", 1, "Material", "Tijolinho de barro", 120.00),
    ("Manutenção", 1, "Material", "Carrinho de mão", 200.00),
    ("Manutenção", 1, "Material", "Arame recuzido", 50.00),
    ("Manutenção", 1, "Material", "Caçamba de entulho", 350.00),
    ("Manutenção", 2, "Material", "Porcelanato", 5750.00),
    ("Manutenção", 2, "Material", "Rejunte de porcelanato", 400.00),
    ("Manutenção", 2, "Material", "Argamassa para o porcelanato", 1800.00),
    ("Manutenção", 2, "Material", "Portas internas", 1500.00),
    ("Manutenção", 2, "Material", "Porta Balcão (R$2000)", 0.00),
    ("Manutenção", 2, "Material", "Vaso", 400.00),
    ("Manutenção", 2, "Material", "Janela (quartos e escritório)", 1700.00),
    ("Manutenção", 2, "Material", "Vitrô Sala", 520.00),
    ("Manutenção", 2, "Material", "Vitrôs banheiros", 400.00),
    ("Manutenção", 2, "Mão de obra", "Eletricista", 3500.00),
    ("Manutenção", 2, "Material", "Quadro de distribuição", 700.00),
    ("Manutenção", 2, "Material", "Conduítes", 2800.00),
    ("Manutenção", 2, "Material", "Lâmpadas", 400.00),
    ("Manutenção", 2, "Material", "Torneiras", 800.00),
    ("Manutenção", 2, "Material", "Sifões e ralos", 250.00),
    ("Manutenção", 2, "Material", "Tomadas", 900.00),
    ("Manutenção", 2, "Material", "Pias e bancadas", 3500.00),
    ("Manutenção", 2, "Material", "Box de vidro para o banheiro (R$850)", 0.00),
    (
        "Manutenção",
        2,
        "Material",
        "Rodapés para acompanhar o porcelanato (R$1500)",
        0.00,
    ),
    ("Manutenção", 2, "Material", "Madeiramento ou estrutura metálica", 4500.00),
    ("Manutenção", 2, "Material", "Calhas e rufos", 1200.00),
    ("Manutenção", 2, "Material", "Caixa de água", 450.00),
    ("Manutenção", 2, "Material", "Dispositivos de segurança", 2000.00),
    ("Manutenção", 3, "Material", "Tinta", 6000.00),
    ("Manutenção", 3, "Material", "Pregos, parafusos, buchas", 200.00),
    ("Manutenção", 3, "Material", "Silicone, espuma expansiva, selante PU", 300.00),
]


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_value(raw: Any) -> float:
    if raw is None or raw == "":
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace(",", ".")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"invalid value: {raw!r}") from exc


def _parse_priority(raw: Any) -> int:
    try:
        priority = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid priority: {raw!r}") from exc
    if priority < 1:
        raise ValueError("priority must be >= 1")
    return priority


class ExpenseStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.csv_path = self.data_dir / "expenses.csv"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        if self.csv_path.is_file():
            rows = self._read_rows()
            if rows:
                return
        stamp = now_stamp()
        seeded: list[dict[str, Any]] = []
        for index, (phase, priority, category, description, value) in enumerate(
            SEED_ROWS, start=1
        ):
            seeded.append(
                {
                    "id": f"EXP_{index:04d}",
                    "phase": phase,
                    "priority": str(priority),
                    "category": category,
                    "description": description,
                    "value": f"{value:.2f}",
                    "created_at": stamp,
                    "updated_at": stamp,
                }
            )
        self._write_rows(seeded)

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.csv_path.is_file():
            return []
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows: list[dict[str, str]] = []
            for raw in reader:
                if not raw:
                    continue
                row = {key: (raw.get(key) or "").strip() for key in HEADERS}
                if not row["id"] and not row["description"]:
                    continue
                rows.append(row)
            return rows

    def _write_rows(self, rows: list[dict[str, Any]]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in HEADERS})

    def _next_id(self, rows: list[dict[str, str]]) -> str:
        max_num = 0
        for row in rows:
            rid = row.get("id") or ""
            if rid.startswith("EXP_"):
                try:
                    max_num = max(max_num, int(rid[4:]))
                except ValueError:
                    continue
        return f"EXP_{max_num + 1:04d}"

    def _normalize_expense(self, row: dict[str, str]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "phase": row["phase"],
            "priority": _parse_priority(row["priority"]),
            "category": row["category"],
            "description": row["description"],
            "value": _parse_value(row["value"]),
            "created_at": row.get("created_at") or "",
            "updated_at": row.get("updated_at") or "",
        }

    def _sort_key(self, expense: dict[str, Any]) -> tuple:
        return (
            expense["phase"].casefold(),
            expense["priority"],
            expense["category"].casefold(),
            expense["description"].casefold(),
            expense["id"],
        )

    def list_expenses(self) -> list[dict[str, Any]]:
        expenses = [self._normalize_expense(row) for row in self._read_rows()]
        expenses.sort(key=self._sort_key)
        return expenses

    def _totals(self, expenses: list[dict[str, Any]]) -> dict[str, Any]:
        by_phase: dict[str, float] = {}
        by_priority: dict[str, float] = {}
        total = 0.0
        for expense in expenses:
            value = float(expense["value"])
            total += value
            phase = expense["phase"]
            by_phase[phase] = by_phase.get(phase, 0.0) + value
            priority_key = str(expense["priority"])
            by_priority[priority_key] = by_priority.get(priority_key, 0.0) + value
        return {
            "all": round(total, 2),
            "by_phase": {k: round(v, 2) for k, v in sorted(by_phase.items())},
            "by_priority": {
                k: round(v, 2) for k, v in sorted(by_priority.items(), key=lambda x: int(x[0]))
            },
        }

    def state(self) -> dict[str, Any]:
        expenses = self.list_expenses()
        return {
            "ok": True,
            "expenses": expenses,
            "totals": self._totals(expenses),
        }

    def upsert_expense(self, payload: dict[str, Any]) -> dict[str, Any]:
        phase = str(payload.get("phase") or "").strip()
        category = str(payload.get("category") or "").strip()
        description = str(payload.get("description") or "").strip()
        if not phase:
            raise ValueError("phase is required")
        if not category:
            raise ValueError("category is required")
        if not description:
            raise ValueError("description is required")

        priority = _parse_priority(payload.get("priority"))
        value = _parse_value(payload.get("value"))
        expense_id = str(payload.get("id") or "").strip()
        stamp = now_stamp()
        rows = self._read_rows()

        if expense_id:
            found = False
            for row in rows:
                if row["id"] == expense_id:
                    row["phase"] = phase
                    row["priority"] = str(priority)
                    row["category"] = category
                    row["description"] = description
                    row["value"] = f"{value:.2f}"
                    row["updated_at"] = stamp
                    if not row.get("created_at"):
                        row["created_at"] = stamp
                    found = True
                    break
            if not found:
                raise ValueError(f"expense not found: {expense_id}")
        else:
            expense_id = self._next_id(rows)
            rows.append(
                {
                    "id": expense_id,
                    "phase": phase,
                    "priority": str(priority),
                    "category": category,
                    "description": description,
                    "value": f"{value:.2f}",
                    "created_at": stamp,
                    "updated_at": stamp,
                }
            )

        self._write_rows(rows)
        expense = next(e for e in self.list_expenses() if e["id"] == expense_id)
        return {"ok": True, "expense": expense, "state": self.state()}

    def delete_expense(self, expense_id: str) -> dict[str, Any]:
        expense_id = (expense_id or "").strip()
        if not expense_id:
            raise ValueError("id is required")
        rows = self._read_rows()
        new_rows = [row for row in rows if row["id"] != expense_id]
        if len(new_rows) == len(rows):
            raise ValueError(f"expense not found: {expense_id}")
        self._write_rows(new_rows)
        return {"ok": True, "deleted": expense_id, "state": self.state()}
