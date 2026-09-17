import csv
from datetime import date
import io
import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from expense_store import ExpenseStore, HEADERS  # noqa: E402
from import_pipeline.pack_types import PRICE_PACK  # noqa: E402
from import_pipeline.pipeline import (  # noqa: E402
    build_quotation_ingestion_prompt,
    commit_rows,
    preview_pack,
)
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
                "category": "Material",
                "description": "Cimento",
                "default_expected_quantity": 2,
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
        self.assertEqual(deleted["expense"]["value"], 0)
        self.assertTrue(deleted["expense"]["scenario"]["unpriced"])

    def test_payment_schedule_crud_validation_and_projection(self) -> None:
        expense = self.store.state()["expenses"][0]
        self.assertEqual(expense["payments"], [])
        self.store.upsert_quotation(self.expense_id, self.quote())
        expense = self.store.state()["expenses"][0]
        self.assertEqual(len(expense["payments"]), 1)
        self.assertEqual(expense["payments"][0]["amount"], 45)
        self.assertEqual(expense["payments"][0]["date_status"], "estimated")
        date.fromisoformat(expense["payments"][0]["date"])

        payload = {
            **expense,
            "payments": [
                {
                    "id": "PAY_001",
                    "date": "2026-10-05",
                    "amount": 40,
                    "date_status": "confirmed",
                },
                {
                    "id": "PAY_002",
                    "date": "2026-11-05",
                    "amount": 60,
                    "date_status": "confirmed",
                },
            ],
        }
        updated = self.store.upsert_expense(payload)["state"]["expenses"][0]
        self.assertEqual([item["amount"] for item in updated["payments"]], [40, 60])
        changed = self.store.upsert_expense(
            {**payload, "payments": [{**payload["payments"][0], "amount": 20}]}
        )["state"]["expenses"][0]
        self.assertEqual(changed["payments"][0]["amount"], 20)
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            self.store.upsert_expense(
                {
                    **payload,
                    "payments": [
                        {
                            "date": "05/10/2026",
                            "amount": 100,
                        }
                    ],
                }
            )


    def test_quotation_records_are_unlimited(self) -> None:
        self.assertEqual(
            self.store.quotation_state(self.expense_id)["quotations"], []
        )
        for index in range(12):
            self.store.upsert_quotation(
                self.expense_id, self.quote(f"Loja {index}", index + 1)
            )
        self.assertEqual(
            12, len(self.store.quotation_state(self.expense_id)["quotations"])
        )

    def test_activity_quantities_drive_planned_minimum_and_maximum(self) -> None:
        first = self.store.upsert_quotation(
            self.expense_id, self.quote("Loja A", 20)
        )["quotation_id"]
        self.store.upsert_quotation(
            self.expense_id,
            {**self.quote("Loja B", 30), "shipping_cost": 0},
        )
        self.store.select_quotation(self.expense_id, first)
        tasks = {
            "version": 3,
            "tasks": [
                {
                    "id": "TASK_0001",
                    "title": "Primeira etapa",
                    "activity_type": "task",
                    "start_date": "2026-10-01",
                    "date_status": "estimated",
                    "expense_allocations": [
                        {
                            "expense_id": self.expense_id,
                            "expected_quantity": 2,
                        }
                    ],
                },
                {
                    "id": "TASK_0002",
                    "title": "Segunda etapa",
                    "activity_type": "task",
                    "start_date": "2026-11-01",
                    "date_status": "confirmed",
                    "expense_allocations": [
                        {
                            "expense_id": self.expense_id,
                            "expected_quantity": 3,
                        }
                    ],
                },
            ],
        }
        (self.data / "tasks.json").write_text(
            json.dumps(tasks), encoding="utf-8"
        )
        expense = self.store.state()["expenses"][0]
        self.assertEqual(5, expense["scenario"]["expected_quantity"])
        self.assertEqual(105, expense["scenario"]["planned"])
        self.assertEqual(105, expense["scenario"]["minimum"])
        self.assertEqual(150, expense["scenario"]["maximum"])
        self.assertEqual(
            [45, 60], [payment["amount"] for payment in expense["payments"]]
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
            "category": "Material",
            "description": "Cimento",
            "unit": "saco",
            "default_expected_quantity": 2,
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

    def test_preview_digest_binds_pack_and_source_documents(self) -> None:
        headers = PRICE_PACK["headers"]
        row = {header: "" for header in headers}
        row.update(
            {
                "id": self.expense_id,
                "unit_price": "10",
                "vendor": "Loja",
                "checked_at": "2026-09-16",
            }
        )
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerow(row)
        pack_text = (
            "===FILE: PRICE_PACK.csv===\n"
            + stream.getvalue()
            + "===END_FILE===\n"
        )
        preview = preview_pack(
            pack_text, source_document_ids=["DOC_B", "DOC_A"]
        )
        self.assertTrue(preview["ok"])
        self.assertEqual(["DOC_A", "DOC_B"], preview["source_document_ids"])
        with self.assertRaisesRegex(ValueError, "preview_digest"):
            commit_rows(
                self.store,
                preview["rows"],
                pack_text=pack_text + "changed",
                source_document_ids=["DOC_A", "DOC_B"],
                preview_digest=preview["preview_digest"],
            )

    def test_source_only_prompt_contains_context_and_evidence(self) -> None:
        source = (
            '<quotation_source type="text" name="message.txt">\n'
            "Loja A: 2 sacos de cimento por R$ 20 cada\n"
            "</quotation_source>"
        )
        result = build_quotation_ingestion_prompt(
            self.store, [self.expense_id], source
        )
        self.assertEqual("quotation-ingestion-prompt.txt", result["filename"])
        self.assertIn("<quotation_sources>", result["prompt"])
        self.assertIn(source, result["prompt"])
        self.assertIn(self.expense_id, result["prompt"])
        self.assertIn("Do not browse", result["prompt"])
        self.assertNotIn("find up to five CURRENT", result["prompt"])

    def test_enriched_metadata_is_validated_and_persisted(self) -> None:
        row = {header: "" for header in PRICE_PACK["headers"]}
        row.update(
            {
                "id": self.expense_id,
                "unit_price": "20",
                "quantity": "2",
                "unit": "saco",
                "vendor": "Loja A",
                "shipping_cost": "5",
                "total_price": "45",
                "checked_at": "2026-09-16",
                "currency": "BRL",
                "brand": "Marca Forte",
                "specifications": "CP II 50 kg",
                "availability": "Em estoque",
                "seller_location": "Nova Odessa - SP",
                "quote_valid_until": "2026-09-30",
                "source_type": "pdf",
                "source_name": "cotacao.pdf",
                "source_page": "2",
                "extraction_confidence": "0.95",
                "ambiguities": "Frete sujeito a confirmação",
            }
        )
        validated = validate_price_rows(
            PRICE_PACK["headers"], [row], PRICE_PACK["headers"]
        )
        self.assertTrue(validated["ok"], validated["errors"])
        result = commit_rows(
            self.store,
            validated["rows"],
            pack_text="===FILE: PRICE_PACK.csv===\n...",
            expense_context=f"{self.expense_id}: Cimento",
        )
        self.assertTrue(result["ok"], result["errors"])
        metadata = self.store.quotation_state(self.expense_id)["quotations"][0][
            "metadata"
        ]
        self.assertEqual("Marca Forte", metadata["brand"])
        self.assertEqual("pdf", metadata["source_type"])
        self.assertEqual(2, metadata["source_page"])
        self.assertEqual(0.95, metadata["extraction_confidence"])

    def test_unknown_metadata_roundtrips(self) -> None:
        payload = self.quote()
        payload["metadata"] = {
            "currency": "BRL",
            "source_type": "manual",
            "custom_evidence": {"reviewer": "Eduardo"},
        }
        quotation_id = self.store.upsert_quotation(
            self.expense_id, payload
        )["quotation_id"]
        quotation = self.store.quotation_state(self.expense_id)["quotations"][0]
        self.assertEqual(
            {"reviewer": "Eduardo"}, quotation["metadata"]["custom_evidence"]
        )
        self.store.upsert_quotation(
            self.expense_id,
            {"id": quotation_id, "notes": "updated", **self.quote()},
        )
        quotation = self.store.quotation_state(self.expense_id)["quotations"][0]
        self.assertEqual(
            {"reviewer": "Eduardo"}, quotation["metadata"]["custom_evidence"]
        )

    def test_pdf_archive_and_ai_upsert_preserve_attachments(self) -> None:
        quotation_id = self.store.upsert_quotation(
            self.expense_id, self.quote()
        )["quotation_id"]
        pdf = b"%PDF-1.4\n1 0 obj<</Type /Page>>endobj\n%%EOF"
        attachment = self.store.quotation_store.add_document(
            self.expense_id, quotation_id, pdf, "../../quote.pdf"
        )
        self.assertEqual("quote.pdf", attachment["original_filename"])
        self.assertEqual(64, len(attachment["sha256"]))
        self.assertEqual(
            pdf,
            self.store.quotation_store.document_path(
                self.expense_id, quotation_id, attachment["id"]
            ).read_bytes(),
        )
        result = self.store.apply_price_rows(
            [
                {
                    "id": self.expense_id,
                    "quotation_id": quotation_id,
                    **self.quote("AI enrichment", 19),
                }
            ]
        )
        self.assertTrue(result["ok"], result["errors"])
        updated = self.store.quotation_state(self.expense_id)["quotations"][0]
        self.assertEqual([attachment["id"]], [a["id"] for a in updated["attachments"]])
        self.store.delete_quotation(self.expense_id, quotation_id)
        archived = next(
            item
            for item in self.store.quotation_store.all()
            if item["id"] == quotation_id
        )
        self.assertTrue(archived["archived"])
        self.assertTrue(self.store.quotation_store.document_path(
            self.expense_id, quotation_id, attachment["id"]
        ).is_file())

    def test_metadata_arithmetic_and_commit_are_revalidated(self) -> None:
        base = {header: "" for header in PRICE_PACK["headers"]}
        base.update(
            {
                "id": self.expense_id,
                "unit_price": "20",
                "quantity": "2",
                "vendor": "Loja A",
                "shipping_cost": "5",
                "total_price": "99",
                "checked_at": "16/09/2026",
                "currency": "USD",
                "source_type": "pdf",
                "source_page": "0",
                "extraction_confidence": "1.5",
            }
        )
        validated = validate_price_rows(
            PRICE_PACK["headers"], [base], PRICE_PACK["headers"]
        )
        self.assertFalse(validated["ok"])
        self.assertTrue(validated["errors"])

        unsafe = {
            "id": self.expense_id,
            **self.quote("Loja inválida", 20),
            "product_url": "javascript:alert(1)",
        }
        committed = commit_rows(
            self.store,
            [unsafe],
            pack_text="resposta inválida",
            expense_context=f"{self.expense_id}: Cimento",
        )
        self.assertFalse(committed["ok"])
        self.assertIn("product_url", committed["fix_text"])
        self.assertIn(self.expense_id, committed["fix_text"])
        self.assertEqual(
            [], self.store.quotation_state(self.expense_id)["quotations"]
        )


class ExpenseQuotationMigrationTests(unittest.TestCase):
    def test_legacy_flat_price_becomes_selected_quotation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            legacy_headers = [
                "id",
                "record_type",
                "priority",
                "category",
                "description",
                "icon_key",
                "value",
                "payments_json",
                "quantity",
                "unit",
                "unit_price",
                "vendor",
                "product_url",
                "price_checked_at",
                "price_notes",
                "quotations_json",
                "selected_quotation_id",
                "provider_id",
                "contract_id",
                "created_at",
                "updated_at",
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
                expense["baseline_quotation_id"],
                expense["quotations"][0]["id"],
            )
            self.assertEqual(expense["quotations"][0]["total_price"], 120)
            self.assertEqual(expense["scenario"]["planned"], 120)


if __name__ == "__main__":
    unittest.main()
