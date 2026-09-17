import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from expense_attachment_store import (  # noqa: E402
    ExpenseAttachmentStore,
    list_system_documents,
    system_document_path,
)
from expense_store import ExpenseStore  # noqa: E402


MINI_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class ExpenseAttachmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name) / "data"
        self.data.mkdir()
        (self.data / "documents").mkdir()
        self.system_a = self.data / "documents" / "sample-contract.pdf"
        self.system_b = self.data / "documents" / "gelson-phase-1-draft.pdf"
        self.system_a.write_bytes(MINI_PDF + b"A")
        self.system_b.write_bytes(MINI_PDF + b"B")
        self.store = ExpenseStore(self.data)
        self.service_id = self.store.upsert_expense(
            {
                "record_type": "service",
                "category": "Mao de obra",
                "description": "Servico teste",
                "unit": "servico",
                "default_expected_quantity": 1,
            }
        )["expense_id"]
        self.material_id = self.store.upsert_expense(
            {
                "record_type": "material",
                "category": "Material",
                "description": "Material teste",
                "unit": "un",
                "default_expected_quantity": 1,
            }
        )["expense_id"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_catalog_lists_all_pdfs(self) -> None:
        documents = list_system_documents(self.data)
        ids = {item["id"] for item in documents}
        self.assertEqual(ids, {"sample-contract", "gelson-phase-1-draft"})
        self.assertTrue(
            all(item["url"].startswith("/api/project/documents/") for item in documents)
        )

    def test_system_document_path_and_aliases(self) -> None:
        target = system_document_path(self.data, "sample-contract")
        self.assertEqual(target, self.system_a.resolve())
        with self.assertRaises(ValueError):
            system_document_path(self.data, "../secret")

    def test_upload_and_remove_on_service_and_material(self) -> None:
        for expense_id in (self.service_id, self.material_id):
            result = self.store.add_expense_document(
                expense_id, MINI_PDF, "orcamento.pdf"
            )
            document = result["document"]
            self.assertEqual(document["source"], "upload")
            self.assertEqual(document["original_filename"], "orcamento.pdf")
            path = self.store.expense_document_path(expense_id, document["id"])
            self.assertTrue(path.is_file())
            self.assertTrue(path.read_bytes().startswith(b"%PDF"))
            expense = next(
                item for item in self.store.list_expenses() if item["id"] == expense_id
            )
            self.assertEqual(len(expense["attachments"]), 1)
            removed = self.store.remove_expense_document(expense_id, document["id"])
            self.assertEqual(removed["deleted"]["id"], document["id"])
            self.assertFalse(path.exists())

    def test_rejects_non_pdf(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add_expense_document(self.service_id, b"not-a-pdf", "x.txt")

    def test_system_link_without_copy(self) -> None:
        result = self.store.link_expense_system_document(
            self.service_id, "sample-contract"
        )
        document = result["document"]
        self.assertEqual(document["source"], "system")
        self.assertEqual(document["system_document_id"], "sample-contract")
        path = self.store.expense_document_path(self.service_id, document["id"])
        self.assertEqual(path, self.system_a.resolve())
        private = self.data / "private" / "expenses"
        copied = list(private.rglob("*.pdf")) if private.exists() else []
        self.assertEqual(copied, [])
        again = self.store.link_expense_system_document(
            self.service_id, "sample-contract"
        )
        self.assertEqual(again["document"]["id"], document["id"])
        self.store.remove_expense_document(self.service_id, document["id"])
        self.assertTrue(self.system_a.exists())

    def test_delete_expense_clears_uploads(self) -> None:
        result = self.store.add_expense_document(self.material_id, MINI_PDF, "nota.pdf")
        path = self.store.expense_document_path(
            self.material_id, result["document"]["id"]
        )
        self.assertTrue(path.is_file())
        self.store.delete_expense(self.material_id)
        self.assertFalse(path.exists())
        payload = json.loads(
            (self.data / "expense-attachments.json").read_text(encoding="utf-8")
        )
        self.assertNotIn(self.material_id, payload.get("by_expense", {}))

    def test_unknown_expense_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add_expense_document("EXP_MISSING", MINI_PDF, "x.pdf")


if __name__ == "__main__":
    unittest.main()
