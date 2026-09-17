import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from quick_task_store import QuickTaskStore  # noqa: E402


class QuickTaskStoreTests(unittest.TestCase):
    def test_simple_crud_and_atomic_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            store = QuickTaskStore(data)
            self.assertEqual([], store.state()["tasks"])

            created = store.upsert({"title": "Comprar lâmpadas"})
            task_id = created["task_id"]
            self.assertEqual(1, created["open_count"])

            updated = store.upsert(
                {"id": task_id, "title": "Comprar lâmpadas LED", "done": True}
            )
            self.assertEqual(0, updated["open_count"])
            self.assertEqual("Comprar lâmpadas LED", updated["tasks"][0]["title"])

            deleted = store.delete(task_id)
            self.assertEqual([], deleted["tasks"])
            document = json.loads(
                (data / "quick-tasks.json").read_text(encoding="utf-8")
            )
            self.assertEqual(1, document["version"])
            self.assertFalse((data / "quick-tasks.json.tmp").exists())

    def test_validation_and_missing_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = QuickTaskStore(Path(directory))
            with self.assertRaises(ValueError):
                store.upsert({"title": ""})
            with self.assertRaises(ValueError):
                store.upsert({"id": "QUICK_9999", "title": "Ausente"})
            with self.assertRaises(ValueError):
                store.delete("QUICK_9999")


if __name__ == "__main__":
    unittest.main()

