from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from expense_store import HEADERS, ExpenseStore  # noqa: E402
from task_store import TaskStore  # noqa: E402


class AllocationPaymentSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)
        manifest = {
            "defaults": {"expense": "home-expense"},
            "icons": {
                "home-expense": {"label": "Despesa", "filename": "home-expense.png"},
                "paint": {"label": "Tinta", "filename": "paint.png"},
            },
        }
        (self.data_dir / "icon-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        with (self.data_dir / "expenses.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADERS)
            writer.writeheader()
            writer.writerow(
                {
                    "id": "EXP_EMPTY",
                    "record_type": "material",
                    "category": "Material",
                    "description": "Sem pagamento",
                    "icon_key": "paint",
                    "unit": "unidade",
                    "default_expected_quantity": "1",
                    "payments_json": "[]",
                }
            )
            writer.writerow(
                {
                    "id": "EXP_OLD",
                    "record_type": "material",
                    "category": "Material",
                    "description": "Data antiga",
                    "icon_key": "paint",
                    "unit": "unidade",
                    "default_expected_quantity": "1",
                    "payments_json": json.dumps(
                        [
                            {
                                "id": "PAY_001",
                                "date": "2027-02-02",
                                "amount": 100.0,
                                "date_status": "estimated",
                                "source": "presumed",
                                "notes": "",
                            }
                        ],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                }
            )
            writer.writerow(
                {
                    "id": "EXP_CONFIRMED",
                    "record_type": "service",
                    "category": "Serviço",
                    "description": "Legado confirmed",
                    "icon_key": "home-expense",
                    "unit": "unidade",
                    "default_expected_quantity": "1",
                    "payments_json": json.dumps(
                        [
                            {
                                "id": "PAY_001",
                                "date": "2026-09-17",
                                "amount": 50.0,
                                "date_status": "confirmed",
                                "source": "manual",
                                "notes": "hist",
                            }
                        ],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                }
            )
        self.expenses = ExpenseStore(self.data_dir)
        self.tasks = TaskStore(self.data_dir)
        macro = self.tasks.upsert(
            self.payload(
                title="Macro",
                activity_type="macro",
                parent_id="",
                expense_allocations=[],
            )
        )
        self.macro_id = macro["task_id"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def payload(self, **overrides):
        item = {
            "title": "Atividade",
            "description": "Teste",
            "priority": 1,
            "sequence": 1,
            "start_date": "2026-09-17",
            "end_date": "2026-10-05",
            "status": "pending",
            "expense_allocations": [],
            "icon_key": "home-expense",
            "date_status": "estimated",
            "activity_type": "task",
            "parent_id": getattr(self, "macro_id", ""),
        }
        item.update(overrides)
        return item

    def test_legacy_confirmed_normalizes_to_estimated_presumed(self) -> None:
        expense = next(
            item
            for item in self.expenses.list_expenses()
            if item["id"] == "EXP_CONFIRMED"
        )
        payment = expense["payments"][0]
        self.assertEqual(payment["date_status"], "estimated")
        self.assertEqual(payment["source"], "presumed")
        self.assertEqual(payment["date"], "2026-09-17")
        self.assertEqual(payment["notes"], "hist")

    def test_upsert_creates_missing_payment_at_task_start(self) -> None:
        self.tasks.upsert(
            self.payload(
                title="Demolição",
                expense_allocations=[
                    {"expense_id": "EXP_EMPTY", "expected_quantity": 1}
                ],
            )
        )
        state = self.expenses.sync_all_allocation_payments()
        expense = next(item for item in state["expenses"] if item["id"] == "EXP_EMPTY")
        self.assertEqual(len(expense["payments"]), 1)
        self.assertEqual(expense["payments"][0]["date"], "2026-09-17")
        self.assertEqual(expense["payments"][0]["source"], "task_start")
        self.assertEqual(expense["payments"][0]["date_status"], "estimated")

    def test_task_start_change_moves_presumed_payments(self) -> None:
        created = self.tasks.upsert(
            self.payload(
                title="Ferramentas",
                end_date="2026-09-20",
                expense_allocations=[{"expense_id": "EXP_OLD", "expected_quantity": 1}],
            )
        )
        self.expenses.sync_all_allocation_payments()
        self.tasks.upsert(
            self.payload(
                id=created["task_id"],
                title="Ferramentas",
                start_date="2026-10-01",
                end_date="2026-10-05",
                expense_allocations=[{"expense_id": "EXP_OLD", "expected_quantity": 1}],
            )
        )
        state = self.expenses.sync_all_allocation_payments()
        expense = next(item for item in state["expenses"] if item["id"] == "EXP_OLD")
        self.assertEqual(expense["payments"][0]["date"], "2026-10-01")
        self.assertEqual(expense["payments"][0]["source"], "task_start")

    def test_multi_task_allocation_creates_payment_per_task(self) -> None:
        self.tasks.upsert(
            self.payload(
                title="Primeira",
                start_date="2026-10-01",
                end_date="2026-10-05",
                expense_allocations=[{"expense_id": "EXP_OLD", "expected_quantity": 1}],
            )
        )
        self.tasks.upsert(
            self.payload(
                title="Segunda",
                start_date="2026-09-17",
                end_date="2026-09-20",
                expense_allocations=[{"expense_id": "EXP_OLD", "expected_quantity": 1}],
            )
        )
        state = self.expenses.sync_all_allocation_payments()
        expense = next(item for item in state["expenses"] if item["id"] == "EXP_OLD")
        dates = sorted(payment["date"] for payment in expense["payments"])
        self.assertEqual(dates, ["2026-09-17", "2026-10-01"])
        self.assertEqual(len(expense["payments"]), 2)
        self.assertTrue(
            all(payment["source"] == "task_start" for payment in expense["payments"])
        )
        self.assertTrue(all(payment.get("task_id") for payment in expense["payments"]))

    def test_validate_payments_coerces_confirmed_input(self) -> None:
        result = self.expenses.upsert_expense(
            {
                "id": "EXP_CONFIRMED",
                "record_type": "service",
                "category": "Serviço",
                "description": "Legado confirmed",
                "unit": "unidade",
                "default_expected_quantity": 1,
                "payments": [
                    {
                        "id": "PAY_001",
                        "date": "2026-11-01",
                        "amount": 12,
                        "date_status": "confirmed",
                        "source": "manual",
                    }
                ],
            }
        )
        payment = result["state"]["expenses"]
        payment = next(item for item in payment if item["id"] == "EXP_CONFIRMED")[
            "payments"
        ][0]
        self.assertEqual(payment["date_status"], "estimated")
        self.assertEqual(payment["source"], "presumed")
        self.assertEqual(payment["date"], "2026-11-01")

    def test_quality_gate_detects_date_drift_then_sync_clears(self) -> None:
        self.tasks.upsert(
            self.payload(
                title="Alinhamento",
                start_date="2026-09-17",
                end_date="2026-09-20",
                expense_allocations=[{"expense_id": "EXP_OLD", "expected_quantity": 1}],
            )
        )
        # Drift: payment still on the seeded 2027-02-02 date.
        before = self.expenses.gantt_payday_quality_gate()
        self.assertFalse(before["ok"])
        self.assertTrue(
            any(
                item["code"]
                in {"date_mismatch", "missing_occurrence_payment", "missing_payment"}
                for item in before["violations"]
            ),
            before["violations"],
        )
        state = self.expenses.sync_all_allocation_payments()
        gate = state["quality_gates"]["gantt_payday"]
        self.assertTrue(gate["ok"], gate["violations"])
        expense = next(item for item in state["expenses"] if item["id"] == "EXP_OLD")
        self.assertEqual(expense["payments"][0]["date"], "2026-09-17")
        self.assertEqual(expense["payments"][0]["source"], "task_start")

    def test_quality_gate_detects_missing_payment(self) -> None:
        self.tasks.upsert(
            self.payload(
                title="Sem pagamento",
                expense_allocations=[
                    {"expense_id": "EXP_EMPTY", "expected_quantity": 1}
                ],
            )
        )
        before = self.expenses.gantt_payday_quality_gate()
        self.assertFalse(before["ok"])
        self.assertTrue(
            any(item["code"] == "missing_payment" for item in before["violations"])
        )
        state = self.expenses.sync_all_allocation_payments()
        self.assertTrue(state["quality_gates"]["gantt_payday"]["ok"])


class LiveGanttPaydayQualityGateTests(unittest.TestCase):
    """Regression gate against the project data directory."""

    def test_live_data_payday_matches_gantt_after_sync(self) -> None:
        data_dir = ROOT / "data"
        if not (data_dir / "expenses.csv").is_file():
            self.skipTest("project data/expenses.csv not present")
        if not (data_dir / "tasks.json").is_file():
            self.skipTest("project data/tasks.json not present")
        store = ExpenseStore(data_dir)
        state = store.sync_all_allocation_payments()
        gate = state["quality_gates"]["gantt_payday"]
        self.assertTrue(
            gate["ok"],
            "Pay Day diverged from Gantt:\n"
            + "\n".join(
                f"- {item.get('message') or item}"
                for item in gate.get("violations", [])
            ),
        )
        self.assertGreater(gate["allocated_count"], 0)


if __name__ == "__main__":
    unittest.main()
