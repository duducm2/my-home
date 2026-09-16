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
    "quantity",
    "unit",
    "unit_price",
    "vendor",
    "product_url",
    "price_checked_at",
    "price_notes",
    "created_at",
    "updated_at",
]

PHASE_ORDER = [
    "Pré-compra",
    "Compra",
    "Na formalização",
    "Pós-mudança",
    "Manutenção",
    "Primeiro ano",
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




def _parse_optional_float(raw: Any) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    return _parse_value(raw)


def _phase_rank(phase: str) -> int:
    try:
        return PHASE_ORDER.index(phase)
    except ValueError:
        return len(PHASE_ORDER)

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
        self._migrate_schema()

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
            qty = "1" if category == "Material" else ""
            seeded.append(
                {
                    "id": f"EXP_{index:04d}",
                    "phase": phase,
                    "priority": str(priority),
                    "category": category,
                    "description": description,
                    "value": f"{value:.2f}",
                    "quantity": qty,
                    "unit": "",
                    "unit_price": "",
                    "vendor": "",
                    "product_url": "",
                    "price_checked_at": "",
                    "price_notes": "",
                    "created_at": stamp,
                    "updated_at": stamp,
                }
            )
        self._write_rows(seeded)

    def _migrate_schema(self) -> None:
        if not self.csv_path.is_file():
            return
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows_raw = list(reader)
        if fieldnames == HEADERS:
            return
        migrated: list[dict[str, Any]] = []
        for raw in rows_raw:
            row = {key: (raw.get(key) or "").strip() for key in HEADERS}
            if not row["id"] and not row["description"]:
                continue
            if not row["quantity"] and row["category"] == "Material":
                row["quantity"] = "1"
            migrated.append(row)
        self._write_rows(migrated)

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
        quantity = _parse_optional_float(row.get("quantity") or "")
        unit_price = _parse_optional_float(row.get("unit_price") or "")
        if quantity is None and row.get("category") == "Material":
            quantity = 1.0
        return {
            "id": row["id"],
            "phase": row["phase"],
            "priority": _parse_priority(row["priority"] or "1"),
            "category": row["category"],
            "description": row["description"],
            "value": _parse_value(row["value"]),
            "quantity": quantity,
            "unit": row.get("unit") or "",
            "unit_price": unit_price,
            "vendor": row.get("vendor") or "",
            "product_url": row.get("product_url") or "",
            "price_checked_at": row.get("price_checked_at") or "",
            "price_notes": row.get("price_notes") or "",
            "created_at": row.get("created_at") or "",
            "updated_at": row.get("updated_at") or "",
        }

    def _sort_key(self, expense: dict[str, Any]) -> tuple:
        return (
            _phase_rank(expense["phase"]),
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
        materials = 0.0
        services = 0.0
        total = 0.0
        for expense in expenses:
            value = float(expense["value"])
            total += value
            phase = expense["phase"]
            by_phase[phase] = by_phase.get(phase, 0.0) + value
            priority_key = str(expense["priority"])
            by_priority[priority_key] = by_priority.get(priority_key, 0.0) + value
            if expense["category"] == "Material":
                materials += value
            else:
                services += value
        ordered_phases = {
            phase: round(by_phase.get(phase, 0.0), 2)
            for phase in PHASE_ORDER
            if phase in by_phase
        }
        for phase, amount in sorted(by_phase.items()):
            if phase not in ordered_phases:
                ordered_phases[phase] = round(amount, 2)
        return {
            "all": round(total, 2),
            "materials": round(materials, 2),
            "services": round(services, 2),
            "by_phase": ordered_phases,
            "by_priority": {
                k: round(v, 2)
                for k, v in sorted(by_priority.items(), key=lambda x: int(x[0]))
            },
        }

    def _timeline(self, expenses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: list[dict[str, Any]] = []
        for phase in PHASE_ORDER:
            phase_items = [e for e in expenses if e["phase"] == phase]
            if not phase_items:
                continue
            if phase == "Manutenção":
                by_pri: dict[int, list] = {}
                for item in phase_items:
                    by_pri.setdefault(item["priority"], []).append(item)
                for pri in sorted(by_pri):
                    items = by_pri[pri]
                    groups.append(
                        {
                            "phase": phase,
                            "priority": pri,
                            "label": f"Manutenção — onda {pri}",
                            "count": len(items),
                            "total": round(sum(i["value"] for i in items), 2),
                            "pending_services": [
                                i for i in items if i["category"] != "Material"
                            ],
                            "items": items,
                        }
                    )
            else:
                groups.append(
                    {
                        "phase": phase,
                        "priority": None,
                        "label": phase,
                        "count": len(phase_items),
                        "total": round(sum(i["value"] for i in phase_items), 2),
                        "pending_services": [
                            i for i in phase_items if i["category"] != "Material"
                        ],
                        "items": phase_items,
                    }
                )
        known = set(PHASE_ORDER)
        extras = [e for e in expenses if e["phase"] not in known]
        if extras:
            groups.append(
                {
                    "phase": "Outros",
                    "priority": None,
                    "label": "Outros",
                    "count": len(extras),
                    "total": round(sum(i["value"] for i in extras), 2),
                    "pending_services": [
                        i for i in extras if i["category"] != "Material"
                    ],
                    "items": extras,
                }
            )
        return groups

    def _materials(self, expenses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [e for e in expenses if e["category"] == "Material"]

    def state(self) -> dict[str, Any]:
        expenses = self.list_expenses()
        return {
            "ok": True,
            "expenses": expenses,
            "totals": self._totals(expenses),
            "timeline": self._timeline(expenses),
            "materials": self._materials(expenses),
            "phase_order": PHASE_ORDER,
        }

    def _apply_price_fields(self, row: dict[str, str], payload: dict[str, Any], stamp: str) -> None:
        if "quantity" in payload and payload.get("quantity") is not None and str(payload.get("quantity")) != "":
            row["quantity"] = f"{_parse_value(payload.get('quantity')):g}"
        if "unit" in payload:
            row["unit"] = str(payload.get("unit") or "").strip()
        if "unit_price" in payload and payload.get("unit_price") is not None and str(payload.get("unit_price")) != "":
            row["unit_price"] = f"{_parse_value(payload.get('unit_price')):.2f}"
        if "vendor" in payload:
            row["vendor"] = str(payload.get("vendor") or "").strip()
        if "product_url" in payload:
            row["product_url"] = str(payload.get("product_url") or "").strip()
        if "price_notes" in payload:
            row["price_notes"] = str(payload.get("price_notes") or "").strip()
        if "price_checked_at" in payload:
            row["price_checked_at"] = str(payload.get("price_checked_at") or "").strip()
        elif any(k in payload for k in ("unit_price", "vendor", "product_url")):
            row["price_checked_at"] = stamp

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
                    self._apply_price_fields(row, payload, stamp)
                    row["updated_at"] = stamp
                    if not row.get("created_at"):
                        row["created_at"] = stamp
                    found = True
                    break
            if not found:
                raise ValueError(f"expense not found: {expense_id}")
        else:
            expense_id = self._next_id(rows)
            row = {
                "id": expense_id,
                "phase": phase,
                "priority": str(priority),
                "category": category,
                "description": description,
                "value": f"{value:.2f}",
                "quantity": "1" if category == "Material" else "",
                "unit": "",
                "unit_price": "",
                "vendor": "",
                "product_url": "",
                "price_checked_at": "",
                "price_notes": "",
                "created_at": stamp,
                "updated_at": stamp,
            }
            self._apply_price_fields(row, payload, stamp)
            rows.append(row)

        self._write_rows(rows)
        expense = next(e for e in self.list_expenses() if e["id"] == expense_id)
        return {"ok": True, "expense": expense, "state": self.state()}

    def apply_price_rows(self, price_rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Apply validated price-pack rows. Match by id, else Material description."""
        stamp = now_stamp()
        rows = self._read_rows()
        by_id = {r["id"]: r for r in rows}
        material_by_desc = {
            r["description"]: r for r in rows if r.get("category") == "Material"
        }
        updated_ids: list[str] = []
        errors: list[str] = []

        for item in price_rows:
            target = None
            eid = str(item.get("id") or "").strip()
            desc = str(item.get("description") or "").strip()
            if eid and eid in by_id:
                target = by_id[eid]
            elif desc and desc in material_by_desc:
                target = material_by_desc[desc]
            else:
                errors.append(f"no match for id={eid!r} description={desc!r}")
                continue

            if "unit_price" in item and item.get("unit_price") is not None and str(item.get("unit_price")) != "":
                target["unit_price"] = f"{_parse_value(item.get('unit_price')):.2f}"
            if "quantity" in item and item.get("quantity") is not None and str(item.get("quantity")) != "":
                target["quantity"] = f"{_parse_value(item.get('quantity')):g}"
            if "unit" in item:
                target["unit"] = str(item.get("unit") or "").strip()
            if "vendor" in item:
                target["vendor"] = str(item.get("vendor") or "").strip()
            if "product_url" in item:
                target["product_url"] = str(item.get("product_url") or "").strip()
            if "price_notes" in item:
                target["price_notes"] = str(item.get("price_notes") or "").strip()
            if "value" in item and item.get("value") is not None and str(item.get("value")).strip() != "":
                target["value"] = f"{_parse_value(item.get('value')):.2f}"
            target["price_checked_at"] = stamp
            target["updated_at"] = stamp
            updated_ids.append(target["id"])

        if errors and not updated_ids:
            raise ValueError("; ".join(errors))

        self._write_rows(rows)
        return {
            "ok": True,
            "updated": updated_ids,
            "errors": errors,
            "state": self.state(),
        }

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
