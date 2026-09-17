import csv
import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from contract_store import ContractStore  # noqa: E402
from expense_store import ExpenseStore  # noqa: E402
from provider_store import ProviderStore  # noqa: E402


class ContractSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name) / "data"
        self.data.mkdir()
        self.providers = ProviderStore(self.data)
        self.provider_id = self.providers.upsert(
            {"name": "Profissional Teste", "service_type": "Pedreiro"}
        )["provider_id"]
        self.expenses = ExpenseStore(self.data)
        self.expense_id = self.expenses.upsert_expense(
            {
                "record_type": "service",
                "priority": 1,
                "category": "Mão de obra",
                "description": "Serviço de teste",
                "unit": "serviço",
                "default_expected_quantity": 1,
            }
        )["expense_id"]
        self.contracts = ContractStore(self.data)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create_contract(self) -> str:
        return self.contracts.upsert(
            {
                "type": "service",
                "title": "Contrato de teste",
                "provider_id": self.provider_id,
                "expense_ids": [self.expense_id],
                "status": "draft",
                "amount": 1000,
                "start_date": "2026-09-16",
            }
        )["contract_id"]

    def test_crud_relationships_and_archive(self) -> None:
        contract_id = self._create_contract()
        item = next(item for item in self.contracts.state()["contracts"] if item["id"] == contract_id)
        self.assertEqual(item["expense_ids"], [self.expense_id])
        with (self.data / "expenses.csv").open(encoding="utf-8", newline="") as handle:
            expense = next(csv.DictReader(handle))
        self.assertEqual(expense["provider_id"], self.provider_id)
        self.assertEqual(expense["contract_id"], contract_id)

        self.contracts.archive(contract_id)
        archived = next(item for item in self.contracts.state()["contracts"] if item["id"] == contract_id)
        self.assertTrue(archived["archived"])
        self.assertEqual(self.contracts.state(include_archived=False)["contracts"], [])

    def test_service_work_period_and_payment_frequencies(self) -> None:
        result = self.contracts.upsert(
            {
                "type": "service",
                "title": "Pagamento semanal",
                "provider_id": self.provider_id,
                "expense_ids": [self.expense_id],
                "status": "active",
                "amount": 1000,
                "start_date": "2026-09-16",
                "end_date": "2026-09-30",
                "payment_frequency": "weekly",
            }
        )
        contract = next(
            item
            for item in result["contracts"]
            if item["id"] == result["contract_id"]
        )
        self.assertEqual(contract["work_days"], 15)
        self.assertEqual(
            [item["date"] for item in contract["payment_schedule"]],
            ["2026-09-16", "2026-09-23", "2026-09-30"],
        )
        self.assertEqual(
            sum(item["amount"] for item in contract["payment_schedule"]),
            1000,
        )

        with self.assertRaisesRegex(ValueError, "equal the total price"):
            self.contracts.upsert(
                {
                    **contract,
                    "payment_frequency": "custom",
                    "payment_schedule": [
                        {
                            "date": "2026-09-20",
                            "amount": 100,
                        }
                    ],
                }
            )

    def test_contract_period_uses_activity_allocations(self) -> None:
        (self.data / "tasks.json").write_text(
            json.dumps(
                {
                    "version": 3,
                    "tasks": [
                        {
                            "id": "TASK_0001",
                            "title": "Serviço alocado",
                            "activity_type": "task",
                            "start_date": "2026-10-02",
                            "end_date": "2026-10-12",
                            "expense_allocations": [
                                {
                                    "expense_id": self.expense_id,
                                    "expected_quantity": 10,
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        result = self.contracts.upsert(
            {
                "type": "service",
                "title": "Contrato alocado",
                "provider_id": self.provider_id,
                "expense_ids": [self.expense_id],
                "status": "active",
                "amount": 1000,
                "payment_frequency": "one_time",
            }
        )
        contract = next(
            item
            for item in result["contracts"]
            if item["id"] == result["contract_id"]
        )
        self.assertEqual("2026-10-02", contract["start_date"])
        self.assertEqual("2026-10-12", contract["end_date"])

    def test_pdf_versions_are_validated_and_preserved(self) -> None:
        contract_id = self._create_contract()
        with self.assertRaisesRegex(ValueError, "PDF"):
            self.contracts.add_document(contract_id, b"not a pdf", "bad.txt")
        first = self.contracts.add_document(
            contract_id, b"%PDF-1.4\n1 0 obj<</Type /Page>>endobj\n%%EOF", "../../first.pdf"
        )["document"]
        second = self.contracts.add_document(
            contract_id, b"%PDF-1.4\n1 0 obj<</Type /Page>>endobj\n% second\n%%EOF", "second.pdf"
        )["document"]
        self.assertEqual(first["id"], "DOC_001")
        self.assertEqual(second["id"], "DOC_002")
        self.assertEqual(second["pages"], 1)
        self.assertEqual(first["original_filename"], "first.pdf")
        self.assertTrue(self.contracts.document_path(contract_id, "DOC_001").is_file())
        self.assertTrue(self.contracts.document_path(contract_id).is_file())

    def test_validation_rejects_invalid_provider_and_material_link(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider"):
            self.contracts.upsert(
                {"type": "service", "title": "Inválido", "provider_id": "MISSING"}
            )
        with self.assertRaisesRegex(ValueError, "materials"):
            self.expenses.upsert_expense(
                {
                    "record_type": "material",
                    "priority": 1,
                    "category": "Material",
                    "description": "Material inválido",
                    "unit": "unidade",
                    "default_expected_quantity": 1,
                    "provider_id": self.provider_id,
                }
            )

    def test_seed_migration_contains_signed_purchase_history(self) -> None:
        payload = json.loads((ROOT / "data" / "contracts.json").read_text(encoding="utf-8"))
        purchase = next(item for item in payload["contracts"] if item["id"] == "CONTRACT_PURCHASE")
        self.assertEqual(purchase["status"], "signed")
        self.assertEqual(purchase["amount"], 310000)
        self.assertEqual(purchase["metadata"]["signature_status"], "17/17 assinaturas")
        self.assertGreaterEqual(len(purchase["document_versions"]), 2)
        self.assertEqual(purchase["current_document_id"], "DOC_002")
        for version in purchase["document_versions"]:
            self.assertTrue((ROOT / version["repository_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
