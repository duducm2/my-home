import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from expense_store import ExpenseStore  # noqa: E402
from provider_store import ProviderStore  # noqa: E402
from quotation_planning_store import QuotationPlanningStore  # noqa: E402


class QuotationWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name) / "data"
        self.data.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_provider_v1_migrates_to_structured_v2(self) -> None:
        legacy = {
            "version": 1,
            "providers": [
                {
                    "id": "PROVIDER_GELSON",
                    "name": "Gelson",
                    "service_type": "Pedreiro",
                    "contact": "11999999999",
                    "custom": {"contract_ids": ["C1", "C2"]},
                }
            ],
        }
        (self.data / "providers.json").write_text(
            json.dumps(legacy), encoding="utf-8"
        )
        provider = ProviderStore(self.data).state()["providers"][0]
        persisted = json.loads(
            (self.data / "providers.json").read_text(encoding="utf-8")
        )
        self.assertEqual(2, persisted["version"])
        self.assertEqual(["Pedreiro"], provider["roles"])
        self.assertEqual("11999999999", provider["phones"][0]["value"])
        self.assertTrue(provider["phones"][0]["primary"])
        self.assertEqual(["C1", "C2"], provider["custom"]["contract_ids"])

    def test_planning_toggles_campaign_and_default_message_persist(self) -> None:
        expense_store = ExpenseStore(self.data)
        expense_id = expense_store.upsert_expense(
            {
                "record_type": "material",
                "category": "Material",
                "description": "Cimento",
                "unit": "saco",
                "default_expected_quantity": 10,
            }
        )["expense_id"]
        expenses = expense_store.list_expenses()
        planning = QuotationPlanningStore(self.data)
        saved = planning.save(
            {
                "selected_category_ids": ["Material"],
                "selected_expense_ids": [expense_id],
                "campaigns": {
                    expense_id: {
                        "status": "contacted",
                        "vendors": [
                            {
                                "provider_id": "PROVIDER_1",
                                "status": "contacted",
                                "contacted_at": "2026-09-16 20:00:00",
                                "notes": "WhatsApp",
                            }
                        ],
                    }
                },
            },
            expenses,
        )
        self.assertIn("Cimento", saved["campaigns"][expense_id]["message"])
        reloaded = QuotationPlanningStore(self.data).state(expenses)
        self.assertEqual(["Material"], reloaded["selected_category_ids"])
        self.assertEqual(
            "PROVIDER_1",
            reloaded["campaigns"][expense_id]["vendors"][0]["provider_id"],
        )


if __name__ == "__main__":
    unittest.main()
