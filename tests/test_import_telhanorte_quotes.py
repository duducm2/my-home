import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import import_telhanorte_quotes as importer  # noqa: E402
from expense_store import ExpenseStore  # noqa: E402
from import_pipeline.pipeline import commit_rows, preview_pack  # noqa: E402


class ImportTelhanorteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.source = self.data / "research" / "telhanorte"
        self.source.mkdir(parents=True)
        self.store = ExpenseStore(self.data)
        self.expense_id = self.store.upsert_expense(
            {
                "record_type": "material",
                "category": "Material",
                "description": "Cimento",
                "unit": "saco (50 kg)",
                "default_expected_quantity": 1,
            }
        )["expense_id"]
        self.scope = self.source / "scope.json"
        self.scope.write_text(
            json.dumps(
                {
                    "location_basis": importer.LOCATION_BASIS,
                    "clusters": {"structural": [self.expense_id]},
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _winner(
        self,
        url: str = "https://www.telhanorte.com.br/cimento-50kg-exemplo-123/p",
    ) -> dict:
        return {
            "matched_product": "Cimento CPII 50 kg",
            "sku": "SKU-1",
            "seller": "Telhanorte",
            "specifications": "Cimento CPII",
            "package_size": "50 kg",
            "displayed_price_brl": 34.9,
            "normalized_unit_price_brl": 34.9,
            "unit": "saco (50 kg)",
            "minimum_quantity": 1,
            "bulk_tiers": [{"minimum_quantity": 50, "unit_price_brl": 33}],
            "freight_brl": None,
            "availability": "available",
            "location_basis": importer.LOCATION_BASIS,
            "checked_at": "2026-09-17",
            "product_url": url,
            "final_url": url,
            "http_status": 200,
            "verification_method": "visible_product_page",
            "caveats": ["Frete desconhecido."],
        }

    def _write_cluster(self, winner: dict | None) -> None:
        (self.source / "cluster-structural.json").write_text(
            json.dumps(
                {
                    "cluster": "structural",
                    "checked_at": "2026-09-17",
                    "location_basis": importer.LOCATION_BASIS,
                    "expenses": [
                        {
                            "expense_id": self.expense_id,
                            "requested_item": "Cimento",
                            "requested_unit": "saco (50 kg)",
                            "match_status": "verified" if winner else "no_match",
                            "candidates": [winner] if winner else [],
                            "winner": winner,
                            "no_match_reason": "" if winner else "Sem produto.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_merge_import_preserves_financial_state_and_records_cep(self) -> None:
        self._write_cluster(self._winner())
        with patch.object(importer, "SOURCE_DIR", self.source), patch.object(
            importer, "SCOPE_PATH", self.scope
        ):
            catalog = importer.merge_catalog(self.store)
        self.assertEqual(catalog["summary"]["verified_matches"], 1)
        rows = importer._pack_rows(catalog, self.store)
        self.assertFalse(rows[0]["selected"])
        self.assertIn("13380", rows[0]["ambiguities"])
        self.assertTrue(rows[0]["quotation_id"].startswith("TELHANORTE_"))
        before = self.store.quotation_state(self.expense_id)["expense"]
        pack_text = importer._pack_text(rows)
        preview = preview_pack(pack_text)
        self.assertTrue(preview["ok"], preview.get("errors"))
        committed = commit_rows(
            self.store,
            preview["rows"],
            pack_text=pack_text,
            preview_digest=preview["preview_digest"],
            preserve_financial_state=True,
        )
        self.assertTrue(committed["ok"])
        after = self.store.quotation_state(self.expense_id)["expense"]
        self.assertEqual(after["value"], before["value"])
        self.assertEqual(after["selected_quotation_id"], "")
        self.assertEqual(after["baseline_quotation_id"], "")
        self.assertEqual(after["quotations"][0]["vendor"], "Telhanorte")

    def test_rejects_non_product_url(self) -> None:
        self._write_cluster(
            self._winner("https://www.telhanorte.com.br/cimento?map=ft")
        )
        with patch.object(importer, "SOURCE_DIR", self.source), patch.object(
            importer, "SCOPE_PATH", self.scope
        ):
            with self.assertRaisesRegex(ValueError, "direct HTTPS Telhanorte /p"):
                importer.merge_catalog(self.store)


if __name__ == "__main__":
    unittest.main()
