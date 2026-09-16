import csv
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from expense_store import ExpenseStore, HEADERS  # noqa: E402
from import_pipeline.pipeline import preview_pack  # noqa: E402
from import_pipeline.validate import validate_price_rows  # noqa: E402


class ExpenseQuotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name) / "data"
        self.data.mkdir()
        self.store = ExpenseStore(self.data)
        self.expense_id = self.store.upsert_expense(
            {
                "record_type": "material",
                "priority": 1,
                "category": "Material",
                "description": "Cimento",
                "value": 100,
                "quantity": 2,
                "unit": "saco",
            }
        )["expense_id"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def quote(self, vendor: str = "Loja A", price: float = 20) -> dict:
        return {
            "vendor": vendor,
            "unit_price": price,
            "quantity": 2,
            "unit": "saco",
            "shipping_cost": 5,
            "product_url": "https://example.com/cimento",
            "checked_at": "2026-09-16",
        }

    def test_manual_crud_selection_projection_and_selected_deletion(self) -> None:
        created = self.store.upsert_quotation(
            self.expense_id, self.quote()
        )
        quotation_id = created["quotation_id"]
        self.assertEqual(len(created["quotations"]), 1)
        selected = self.store.select_quotation(
            self.expense_id, quotation_id
        )
        self.assertEqual(selected["expense"]["value"], 45)
        self.assertEqual(selected["expense"]["vendor"], "Loja A")
        self.assertEqual(
            selected["expense"]["selected_quotation_id"], quotation_id
        )

        self.store.upsert_quotation(
            self.expense_id,
            {"id": quotation_id, **self.quote("Loja B", 25)},
        )
        self.assertEqual(
            self.store.quotation_state(self.expense_id)["expense"]["value"], 55
        )
        deleted = self.store.delete_quotation(
            self.expense_id, quotation_id
        )
        self.assertEqual(deleted["selected_quotation_id"], "")
        self.assertEqual(deleted["quotations"], [])
        self.assertEqual(deleted["expense"]["value"], 55)

    def test_zero_five_and_six_quotation_boundaries(self) -> None:
        self.assertEqual(
            self.store.quotation_state(self.expense_id)["quotations"], []
        )
        for index in range(5):
            self.store.upsert_quotation(
                self.expense_id, self.quote(f"Loja {index}", index + 1)
            )
        with self.assertRaisesRegex(ValueError, "at most 5"):
            self.store.upsert_quotation(
                self.expense_id, self.quote("Loja 6", 6)
            )

    def test_invalid_numbers_urls_and_duplicate_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite nonnegative"):
            self.store.upsert_quotation(
                self.expense_id, self.quote(price=float("inf"))
            )
        invalid = self.quote()
        invalid["product_url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(ValueError, "HTTP"):
            self.store.upsert_quotation(self.expense_id, invalid)
        payload = {
            "id": self.expense_id,
            "record_type": "material",
            "priority": 1,
            "category": "Material",
            "description": "Cimento",
            "value": 100,
            "quotations": [
                {"id": "same", **self.quote()},
                {"id": "same", **self.quote("Loja B")},
            ],
        }
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.store.upsert_expense(payload)

    def test_ai_import_is_grouped_and_atomic(self) -> None:
        rows = [
            {"id": self.expense_id, **self.quote("IA 1", 18)},
            {"id": self.expense_id, **self.quote("IA 2", 19)},
        ]
        result = self.store.apply_price_rows(rows)
        self.assertTrue(result["ok"])
        self.assertEqual(
            [item["source"] for item in self.store.quotation_state(
                self.expense_id
            )["quotations"]],
            ["ai", "ai"],
        )
        rejected = self.store.apply_price_rows(
            [
                {"id": self.expense_id, **self.quote("IA 3", 17)},
                {"id": "EXP_UNKNOWN", **self.quote("IA inválida", 1)},
            ]
        )
        self.assertFalse(rejected["ok"])
        self.assertEqual(
            len(
                self.store.quotation_state(self.expense_id)["quotations"]
            ),
            2,
        )

    def test_deleting_expense_removes_embedded_quotations(self) -> None:
        self.store.upsert_quotation(self.expense_id, self.quote())
        self.store.delete_expense(self.expense_id)
        with self.assertRaisesRegex(ValueError, "expense not found"):
            self.store.quotation_state(self.expense_id)

    def test_validation_and_iterative_fix_prompt(self) -> None:
        headers = ["id", "unit_price", "vendor", "product_url"]
        validated = validate_price_rows(
            headers,
            [
                {
                    "id": self.expense_id,
                    "unit_price": "10",
                    "vendor": "Loja",
                    "product_url": "https://example.com/item",
                }
            ],
            headers,
        )
        self.assertTrue(validated["ok"])
        broken = preview_pack(
            "resposta sem marcadores",
            correction_instructions="Mantenha o fornecedor regional.",
            expense_context=f"{self.expense_id}: Cimento",
        )
        self.assertFalse(broken["ok"])
        self.assertIn("resposta sem marcadores", broken["fix_text"])
        self.assertIn("Mantenha o fornecedor regional", broken["fix_text"])
        self.assertIn(self.expense_id, broken["fix_text"])


class ExpenseQuotationMigrationTests(unittest.TestCase):
    def test_legacy_flat_price_becomes_selected_quotation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            legacy_headers = [
                item
                for item in HEADERS
                if item not in {"quotations_json", "selected_quotation_id"}
            ]
            row = {key: "" for key in legacy_headers}
            row.update(
                {
                    "id": "EXP_0001",
                    "record_type": "material",
                    "priority": "1",
                    "category": "Material",
                    "description": "Areia",
                    "value": "120.00",
                    "quantity": "3",
                    "unit": "m3",
                    "unit_price": "40.00",
                    "vendor": "Depósito",
                    "product_url": "https://example.com/areia",
                }
            )
            with (data / "expenses.csv").open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=legacy_headers)
                writer.writeheader()
                writer.writerow(row)
            expense = ExpenseStore(data).list_expenses()[0]
            self.assertEqual(len(expense["quotations"]), 1)
            self.assertEqual(
                expense["selected_quotation_id"],
                expense["quotations"][0]["id"],
            )
            self.assertEqual(expense["quotations"][0]["total_price"], 120)


if __name__ == "__main__":
    unittest.main()
