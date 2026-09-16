from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from expense_store import HEADERS  # noqa: E402
from note_store import NoteStore  # noqa: E402
from task_store import TaskStore  # noqa: E402


class TaskStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)
        manifest = {
            "defaults": {"expense": "home-expense"},
            "icons": {
                "home-expense": {"label": "Despesa", "filename": "home-expense.png"}
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
                    "id": "EXP_0001",
                    "priority": "1",
                    "category": "Material",
                    "description": "Cimento",
                    "icon_key": "home-expense",
                    "value": "100.00",
                }
            )
        self.store = TaskStore(self.data_dir)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def payload(**overrides):
        item = {
            "title": "Preparar obra",
            "description": "Teste",
            "priority": 2,
            "sequence": 3,
            "start_date": "2026-09-16",
            "end_date": "2026-09-18",
            "status": "pending",
            "expense_id": "EXP_0001",
            "icon_key": "home-expense",
            "date_status": "estimated",
        }
        item.update(overrides)
        return item

    def test_crud_sorting_and_sequence_normalization(self) -> None:
        later = self.store.upsert(
            self.payload(title="Prioridade baixa", priority=3, sequence=9)
        )
        first = self.store.upsert(
            self.payload(title="Prioridade alta", priority=1, sequence=9)
        )
        tasks = first["tasks"]
        self.assertEqual(
            ["Prioridade alta", "Prioridade baixa"], [task["title"] for task in tasks]
        )
        self.assertEqual([1, 2], [task["sequence"] for task in tasks])
        task_id = later["task_id"]
        current = next(
            task for task in self.store.list_tasks() if task["id"] == task_id
        )
        current.update(
            {"priority": 1, "start_date": "2026-10-01", "end_date": "2026-10-05"}
        )
        updated = self.store.upsert(current)
        changed = next(task for task in updated["tasks"] if task["id"] == task_id)
        self.assertEqual("2026-10-01", changed["start_date"])
        deleted = self.store.delete(task_id)
        self.assertEqual(1, deleted["count"])
        self.assertEqual([1], [task["sequence"] for task in deleted["tasks"]])

    def test_rejects_invalid_fields(self) -> None:
        invalid = [
            self.payload(title=""),
            self.payload(priority=0),
            self.payload(sequence=0),
            self.payload(start_date="16/09/2026"),
            self.payload(start_date="2026-09-20", end_date="2026-09-18"),
            self.payload(status="unknown"),
            self.payload(expense_id="EXP_9999"),
            self.payload(icon_key="missing"),
            self.payload(date_status="maybe"),
        ]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.store.upsert(payload)

    def test_atomic_file_remains_valid_json(self) -> None:
        self.store.upsert(self.payload())
        document = json.loads(
            (self.data_dir / "tasks.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, len(document["tasks"]))
        self.assertFalse((self.data_dir / "tasks.json.tmp").exists())


class NoteStoreTests(unittest.TestCase):
    def test_notes_are_saved_and_loaded_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = NoteStore(Path(directory))
            self.assertEqual("", store.load()["text"])
            saved = store.save({"text": "Lembrar de conferir o orçamento."})
            self.assertEqual("Lembrar de conferir o orçamento.", saved["text"])
            self.assertEqual(saved["text"], NoteStore(Path(directory)).load()["text"])
            self.assertFalse((Path(directory) / "general-notes.json.tmp").exists())

    def test_notes_have_a_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                NoteStore(Path(directory)).save({"text": "x" * 100_001})


class MigrationIntegrityTests(unittest.TestCase):
    def test_cashflow_projection_totals_and_interpolation(self) -> None:
        projection = json.loads(
            (ROOT / "data" / "cashflow-projection.json").read_text(encoding="utf-8")
        )
        months = projection["months"]
        self.assertEqual(16, len(months))
        self.assertEqual("2026-09", months[0]["month"])
        self.assertTrue(months[0]["estimated"])
        self.assertEqual(2930.0, months[0]["net_savings"])
        self.assertEqual(35180.0, sum(month["net_savings"] for month in months))
        self.assertEqual(184000.0, sum(month["gross_income"] for month in months))
        self.assertEqual(
            148820.0,
            sum(month["gross_income"] - month["net_savings"] for month in months),
        )
        category_keys = [category["key"] for category in projection["categories"]]
        self.assertEqual(
            148820.0,
            sum(month[key] for month in months for key in category_keys),
        )

    def test_repository_data_uses_tasks_without_phase_fields(self) -> None:
        tasks = json.loads((ROOT / "data" / "tasks.json").read_text(encoding="utf-8"))[
            "tasks"
        ]
        self.assertGreater(len(tasks), 0)
        self.assertTrue(all(task["date_status"] == "estimated" for task in tasks))
        self.assertEqual(
            tasks, sorted(tasks, key=lambda item: (item["priority"], item["sequence"]))
        )
        with (ROOT / "data" / "expenses.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            self.assertNotIn("phase", csv.DictReader(handle).fieldnames or [])
        project = json.loads(
            (ROOT / "data" / "project.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("phases", project)

    def test_every_expense_and_task_has_a_served_icon(self) -> None:
        manifest = json.loads(
            (ROOT / "data" / "icon-manifest.json").read_text(encoding="utf-8")
        )
        icons = manifest["icons"]
        with (ROOT / "data" / "expenses.csv").open(
            "r", encoding="utf-8-sig", newline=""
        ) as handle:
            expenses = list(csv.DictReader(handle))
        tasks = json.loads((ROOT / "data" / "tasks.json").read_text(encoding="utf-8"))[
            "tasks"
        ]
        for item in [*expenses, *tasks]:
            with self.subTest(item=item["id"]):
                key = item.get("icon_key")
                self.assertIn(key, icons)
                self.assertTrue(
                    (
                        ROOT / "web" / "assets" / "item-icons" / icons[key]["filename"]
                    ).is_file()
                )


if __name__ == "__main__":
    unittest.main()
