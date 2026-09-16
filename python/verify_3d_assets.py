"""Validate the committed local 3D library without loading network resources."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "web" / "assets" / "models"
EXPECTED_IDS = {
    "sofa",
    "bed",
    "table",
    "chair",
    "wardrobe",
    "refrigerator",
    "stove",
    "plant",
    "tree",
    "television",
    "coffee_table",
    "bookshelf",
    "desk_lamp",
    "ceiling_lamp",
    "office_desk",
    "office_chair",
    "single_bed",
    "nightstand",
    "dresser",
    "mirror",
    "kitchen_cabinet",
    "microwave",
    "trash_can",
    "laundry_cart",
    "outdoor_set",
    "outdoor_bench",
    "picnic_table",
    "drill",
    "ladder",
    "toolbox",
    "tool_cart",
    "cement_bag",
    "paint_cans",
    "work_light",
    "plunger",
    "water_container",
    "wall_clock",
}
MAX_ASSET_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_TOTAL_TRIANGLES = 1_000_000
SUPPORTED_REQUIRED_EXTENSIONS = {
    "KHR_materials_clearcoat",
    "KHR_materials_emissive_strength",
    "KHR_materials_ior",
    "KHR_materials_transmission",
    "KHR_materials_volume",
    "KHR_texture_transform",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def glb_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        magic, version, length = struct.unpack("<4sII", handle.read(12))
        if magic != b"glTF" or version != 2 or length != path.stat().st_size:
            raise ValueError(f"{path.name}: invalid GLB header")
        chunk_length, chunk_type = struct.unpack("<II", handle.read(8))
        if chunk_type != 0x4E4F534A:
            raise ValueError(f"{path.name}: first GLB chunk is not JSON")
        return json.loads(handle.read(chunk_length).decode("utf-8").rstrip("\x00 "))


def triangle_count(document: dict[str, Any]) -> int:
    accessors = document.get("accessors") or []
    total = 0
    for mesh in document.get("meshes") or []:
        for primitive in mesh.get("primitives") or []:
            if primitive.get("mode", 4) != 4:
                continue
            index = primitive.get("indices")
            if index is not None:
                total += int(accessors[index].get("count") or 0) // 3
            else:
                position = (primitive.get("attributes") or {}).get("POSITION")
                if position is not None:
                    total += int(accessors[position].get("count") or 0) // 3
    return total


def validate_library() -> list[dict[str, Any]]:
    manifest = json.loads((MODEL_DIR / "manifest.json").read_text(encoding="utf-8"))
    assets = manifest.get("assets") or []
    assert manifest.get("runtime_network_required") is False
    assert {asset.get("id") for asset in assets} == EXPECTED_IDS
    reports = []
    total_bytes = 0
    total_triangles = 0
    for asset in assets:
        assert asset.get("author") and asset.get("source_url", "").startswith("https://")
        assert asset.get("license") in {"CC0-1.0", "CC-BY-4.0"}
        assert all(
            float(asset.get(key) or 0) > 0
            for key in ("width_m", "height_m", "depth_m")
        )
        model_url = str(asset.get("model_url") or "")
        assert model_url.startswith("/assets/models/") and "://" not in model_url
        model_path = ROOT / "web" / model_url.lstrip("/")
        assert model_path.is_file()
        assert model_path.stat().st_size == asset.get("bytes")
        assert model_path.stat().st_size <= MAX_ASSET_BYTES
        assert file_hash(model_path) == asset.get("sha256")
        preview_url = str(asset.get("preview_url") or "")
        assert preview_url.startswith("/assets/models/previews/")
        assert (ROOT / "web" / preview_url.lstrip("/")).is_file()
        document = glb_json(model_path)
        unsupported = set(document.get("extensionsRequired") or []) - SUPPORTED_REQUIRED_EXTENSIONS
        assert not unsupported, f"{asset['id']}: unsupported extensions {unsupported}"
        triangles = triangle_count(document)
        total_bytes += model_path.stat().st_size
        total_triangles += triangles
        reports.append(
            {"id": asset["id"], "bytes": model_path.stat().st_size, "triangles": triangles}
        )
    assert total_bytes <= MAX_TOTAL_BYTES
    assert total_triangles <= MAX_TOTAL_TRIANGLES
    return reports


if __name__ == "__main__":
    result = validate_library()
    for item in result:
        print(f"{item['id']}: {item['bytes'] / 1_000_000:.2f} MB, {item['triangles']:,} triangles")
    print(
        f"OK: {len(result)} local assets, "
        f"{sum(item['bytes'] for item in result) / 1_000_000:.2f} MB, "
        f"{sum(item['triangles'] for item in result):,} triangles"
    )
