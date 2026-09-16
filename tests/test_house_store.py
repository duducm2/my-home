import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from house_store import HouseStore  # noqa: E402


class HouseStoreEditorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data = Path(self.temporary.name) / "data"
        self.data.mkdir()
        self.house_path = self.data / "house.json"
        self.house_path.write_text(
            json.dumps(
                {
                    "name": "Casa teste",
                    "model_3d": {
                        "lot": {"width_m": 12, "depth_m": 27},
                        "rooms": [{"id": "sala"}],
                        "layout_overrides": {},
                        "placed_assets": [],
                    },
                }
            ),
            encoding="utf-8",
        )
        self.store = HouseStore(self.data)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def asset(asset_id: str = "asset_sofa", asset_type: str = "sofa") -> dict:
        return {
            "id": asset_id,
            "asset_type": asset_type,
            "label": "Sofá",
            "x_m": 2,
            "y_m": 0,
            "z_m": 3,
            "width_m": 2,
            "height_m": 0.8,
            "depth_m": 0.9,
            "rotation_y_deg": 15,
            "color": "#8f6f61",
            "parent_kind": "room",
            "parent_id": "sala",
        }

    def test_layout_round_trip_preserves_house_and_is_atomic(self) -> None:
        result = self.store.save_model3d_layout(
            {
                "layout_overrides": {
                    "room:sala": {
                        "translation_m": {"x": 0.5, "y": 0, "z": -0.25},
                        "rotation_y_deg": 15,
                        "scale": {"x": 1.1, "y": 1, "z": 0.9},
                    }
                },
                "placed_assets": [self.asset()],
            }
        )
        self.assertTrue(result["ok"])
        loaded = self.store.load()["house"]
        self.assertEqual(loaded["name"], "Casa teste")
        self.assertEqual(loaded["model_3d"]["placed_assets"][0]["id"], "asset_sofa")
        self.assertEqual(
            loaded["model_3d"]["layout_overrides"]["room:sala"]["translation_m"]["x"],
            0.5,
        )
        self.assertFalse(self.house_path.with_suffix(".json.tmp").exists())
        json.loads(self.house_path.read_text(encoding="utf-8"))

    def test_rejects_unknown_assets_and_out_of_bounds_placement(self) -> None:
        bad_type = self.asset()
        bad_type["asset_type"] = "spaceship"
        with self.assertRaisesRegex(ValueError, "asset_type"):
            self.store.save_model3d_layout(
                {"layout_overrides": {}, "placed_assets": [bad_type]}
            )
        out_of_bounds = self.asset()
        out_of_bounds["x_m"] = 50
        with self.assertRaisesRegex(ValueError, "x_m"):
            self.store.save_model3d_layout(
                {"layout_overrides": {}, "placed_assets": [out_of_bounds]}
            )

    def test_manifest_asset_and_builtin_primitive_can_be_persisted(self) -> None:
        assets = [
            self.asset("asset_security_camera", "security_camera"),
            self.asset("asset_box", "box"),
        ]
        result = self.store.save_model3d_layout(
            {"layout_overrides": {}, "placed_assets": assets}
        )
        self.assertEqual(
            [asset["asset_type"] for asset in result["placed_assets"]],
            ["security_camera", "box"],
        )

    def test_rejects_malformed_overrides_and_duplicate_asset_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "override key"):
            self.store.save_model3d_layout(
                {"layout_overrides": {"../../room": {}}, "placed_assets": []}
            )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.store.save_model3d_layout(
                {
                    "layout_overrides": {},
                    "placed_assets": [self.asset(), self.asset()],
                }
            )

    def test_inline_house_name_is_validated_and_preserves_house_data(self) -> None:
        result = self.store.save_name("  Casa   dos Sonhos  ")
        self.assertEqual(result["house"]["display_name"], "Casa dos Sonhos")
        self.assertIn("model_3d", result["house"])
        with self.assertRaisesRegex(ValueError, "required"):
            self.store.save_name("   ")
        with self.assertRaisesRegex(ValueError, "80"):
            self.store.save_name("x" * 81)

    def test_repository_house_has_editor_collections(self) -> None:
        house = json.loads((ROOT / "data" / "house.json").read_text(encoding="utf-8"))
        self.assertIsInstance(house["model_3d"]["layout_overrides"], dict)
        self.assertIsInstance(house["model_3d"]["placed_assets"], list)


if __name__ == "__main__":
    unittest.main()
