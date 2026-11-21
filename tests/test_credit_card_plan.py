"""Tests for CreditCardPlanStore and its HTTP endpoints."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from credit_card_plan_store import CreditCardPlanStore, MAX_EXPENSE_IDS  # noqa: E402
from expense_server import ExpenseHandler  # noqa: E402


class CreditCardPlanStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.store = CreditCardPlanStore(self.data_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initial_load_creates_empty_plan(self) -> None:
        loaded = self.store.load()
        self.assertTrue(loaded["ok"])
        self.assertEqual([], loaded["expense_ids"])
        self.assertTrue((self.data_dir / "credit-card-plan.json").is_file())

    def test_save_deduplicates_strips_and_persists(self) -> None:
        saved = self.store.save(
            {"expense_ids": [" EXP_0003 ", "EXP_0005", "EXP_0003", "", "  "]}
        )
        self.assertEqual(["EXP_0003", "EXP_0005"], saved["expense_ids"])

        reloaded = CreditCardPlanStore(self.data_dir).load()
        self.assertEqual(["EXP_0003", "EXP_0005"], reloaded["expense_ids"])

    def test_save_rejects_invalid_payloads(self) -> None:
        with self.assertRaises(ValueError):
            self.store.save("not-an-object")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.store.save({"expense_ids": "EXP_0001"})
        with self.assertRaises(ValueError):
            self.store.save(
                {"expense_ids": [f"EXP_{i}" for i in range(MAX_EXPENSE_IDS + 1)]}
            )


class CreditCardPlanEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

        class IsolatedHandler(ExpenseHandler):
            data_dir = self.data_dir

            def log_message(self, format: str, *args: object) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), IsolatedHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.temp_dir.cleanup()

    def test_get_and_post_credit_card_plan(self) -> None:
        base = f"http://127.0.0.1:{self.port}/api/credit-card-plan"
        with urllib.request.urlopen(base) as response:
            initial = json.loads(response.read().decode("utf-8"))
        self.assertTrue(initial["ok"])
        self.assertEqual([], initial["expense_ids"])

        req = urllib.request.Request(
            base,
            data=json.dumps({"expense_ids": ["EXP_0003", "EXP_0009"]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            updated = json.loads(response.read().decode("utf-8"))
        self.assertEqual(["EXP_0003", "EXP_0009"], updated["expense_ids"])

        with urllib.request.urlopen(base) as response:
            fetched = json.loads(response.read().decode("utf-8"))
        self.assertEqual(["EXP_0003", "EXP_0009"], fetched["expense_ids"])
