import json
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
        self.assertEqual(len(reports), 97)
        self.assertTrue(all(report["triangles"] > 0 for report in reports))

    def test_generated_editor_catalog_matches_manifest(self) -> None:
        model_dir = ROOT / "web" / "assets" / "models"
        manifest = json.loads(
            (model_dir / "manifest.json").read_text(encoding="utf-8")
        )
        source = (model_dir / "asset-catalog.js").read_text(encoding="utf-8")
        catalog = json.loads(source.split("=", 1)[1].strip().removesuffix(";"))
        self.assertEqual(set(catalog), EXPECTED_IDS)
        self.assertEqual(
            set(catalog), {asset["id"] for asset in manifest["assets"]}
        )
        self.assertTrue(
            all(
                entry["modelUrl"].endswith(f"/{asset_id}.glb")
                and entry["previewUrl"]
                and entry["group"]
                and all(entry[axis] > 0 for axis in ("width", "height", "depth"))
                and "keywords" in entry
                for asset_id, entry in catalog.items()
            )
        )


if __name__ == "__main__":
    unittest.main()
