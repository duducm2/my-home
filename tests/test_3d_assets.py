import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from verify_3d_assets import EXPECTED_IDS, validate_library  # noqa: E402


class Local3DAssetLibraryTests(unittest.TestCase):
    def test_manifest_models_licenses_hashes_and_budgets(self) -> None:
        reports = validate_library()
        self.assertEqual({report["id"] for report in reports}, EXPECTED_IDS)
        self.assertTrue(all(report["triangles"] > 0 for report in reports))


if __name__ == "__main__":
    unittest.main()
