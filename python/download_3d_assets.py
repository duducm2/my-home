"""Download and package the local, licensed 3D asset library.

Run from the repository root:
    python python/download_3d_assets.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "assets" / "models"
POLYHAVEN_API = "https://api.polyhaven.com"
GROUP_COLORS = {
    "Sala": "#8f6f61",
    "Quarto": "#a7b8cc",
    "Cozinha e serviço": "#d7dde0",
    "Decoração": "#4f8c58",
    "Exterior": "#477a4f",
    "Escritório": "#8b7f72",
    "Iluminação": "#e0bc62",
    "Banheiro": "#87b6c9",
    "Ferramentas e obra": "#c48645",
}

ASSETS: list[dict[str, Any]] = [
    {"id": "sofa", "label": "Sofá", "group": "Sala", "slug": "Sofa_01", "dimensions": [2.0, 0.78, 0.85]},
    {"id": "bed", "label": "Cama de casal", "group": "Quarto", "slug": "vintage_day_bed", "dimensions": [1.4, 0.6, 1.9]},
    {"id": "table", "label": "Mesa de jantar", "group": "Sala", "slug": "dining_table", "dimensions": [1.4, 0.76, 0.8]},
    {"id": "chair", "label": "Cadeira", "group": "Sala", "slug": "painted_wooden_chair_01", "dimensions": [0.48, 0.9, 0.48]},
    {"id": "wardrobe", "label": "Guarda-roupa", "group": "Quarto", "slug": "modern_wooden_cabinet", "dimensions": [1.6, 2.1, 0.58]},
    {"id": "stove", "label": "Fogão", "group": "Cozinha e serviço", "slug": "electric_stove", "dimensions": [0.62, 0.9, 0.64]},
    {"id": "plant", "label": "Planta em vaso", "group": "Decoração", "slug": "potted_plant_04", "dimensions": [0.5, 1.1, 0.5]},
    {
        "id": "tree",
        "label": "Árvore",
        "group": "Exterior",
        "slug": "tree_small_02",
        "dimensions": [3.2, 5.0, 3.2],
        "simplify_ratio": 0.025,
    },
    {
        "id": "refrigerator",
        "label": "Geladeira",
        "group": "Cozinha e serviço",
        "dimensions": [0.72, 1.85, 0.7],
        "direct_url": "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/CommercialRefrigerator/glTF-Binary/CommercialRefrigerator.glb",
        "direct_preview_url": "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/CommercialRefrigerator/screenshot/screenshot.jpg",
        "source_url": "https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CommercialRefrigerator",
        "author": "Sean Thomas; Eric Chadwick; Darmstadt Graphics Group GmbH",
        "license": "CC-BY-4.0",
    },
    {"id": "television", "label": "Televisão", "group": "Sala", "slug": "Television_01", "dimensions": [1.25, 0.75, 0.12]},
    {"id": "coffee_table", "label": "Mesa de centro", "group": "Sala", "slug": "CoffeeTable_01", "dimensions": [1.1, 0.42, 0.62]},
    {"id": "bookshelf", "label": "Estante", "group": "Sala", "slug": "Shelf_01", "dimensions": [1.1, 1.9, 0.38]},
    {"id": "desk_lamp", "label": "Luminária de mesa", "group": "Escritório", "slug": "desk_lamp_arm_01", "dimensions": [0.35, 0.55, 0.35]},
    {"id": "ceiling_lamp", "label": "Luminária de teto", "group": "Iluminação", "slug": "modern_ceiling_lamp_01", "dimensions": [0.48, 0.55, 0.48]},
    {"id": "office_desk", "label": "Mesa de escritório", "group": "Escritório", "slug": "metal_office_desk", "dimensions": [1.4, 0.76, 0.7]},
    {"id": "office_chair", "label": "Cadeira de escritório", "group": "Escritório", "slug": "painted_wooden_chair_02", "dimensions": [0.52, 0.92, 0.52]},
    {"id": "single_bed", "label": "Cama de solteiro", "group": "Quarto", "slug": "old_bed_frame", "dimensions": [0.95, 0.62, 1.95]},
    {"id": "nightstand", "label": "Criado-mudo", "group": "Quarto", "slug": "ClassicNightstand_01", "dimensions": [0.5, 0.62, 0.42]},
    {"id": "dresser", "label": "Cômoda", "group": "Quarto", "slug": "drawer_cabinet", "dimensions": [1.05, 0.95, 0.5]},
    {"id": "mirror", "label": "Espelho", "group": "Banheiro", "slug": "ornate_mirror_01", "dimensions": [0.75, 1.05, 0.08]},
    {"id": "kitchen_cabinet", "label": "Armário de cozinha", "group": "Cozinha e serviço", "slug": "painted_wooden_cabinet", "dimensions": [1.2, 1.9, 0.48]},
    {"id": "microwave", "label": "Micro-ondas", "group": "Cozinha e serviço", "slug": "vintage_microwave", "dimensions": [0.52, 0.32, 0.42]},
    {"id": "trash_can", "label": "Lixeira", "group": "Cozinha e serviço", "slug": "metal_trash_can", "dimensions": [0.38, 0.62, 0.38]},
    {"id": "laundry_cart", "label": "Carrinho de lavanderia", "group": "Cozinha e serviço", "slug": "industrial_storage_cart", "dimensions": [0.75, 0.9, 0.48]},
    {"id": "outdoor_set", "label": "Conjunto externo", "group": "Exterior", "slug": "outdoor_table_chair_set_01", "dimensions": [2.4, 0.9, 2.4], "simplify_ratio": 0.35},
    {"id": "outdoor_bench", "label": "Banco externo", "group": "Exterior", "slug": "painted_wooden_bench", "dimensions": [1.7, 0.9, 0.65]},
    {"id": "picnic_table", "label": "Mesa de piquenique", "group": "Exterior", "slug": "wooden_picnic_table", "dimensions": [1.8, 0.78, 1.5]},
    {"id": "drill", "label": "Furadeira", "group": "Ferramentas e obra", "slug": "Drill_01", "dimensions": [0.32, 0.24, 0.1]},
    {"id": "ladder", "label": "Escada", "group": "Ferramentas e obra", "slug": "ladder_sectioned_01", "dimensions": [0.55, 2.6, 0.18]},
    {"id": "toolbox", "label": "Caixa de ferramentas", "group": "Ferramentas e obra", "slug": "metal_toolbox", "dimensions": [0.55, 0.3, 0.28]},
    {"id": "tool_cart", "label": "Carrinho de ferramentas", "group": "Ferramentas e obra", "slug": "tool_cart", "dimensions": [0.78, 0.95, 0.5]},
    {"id": "cement_bag", "label": "Saco de cimento", "group": "Ferramentas e obra", "slug": "cement_bag", "dimensions": [0.62, 0.14, 0.42]},
    {"id": "paint_cans", "label": "Latas de tinta", "group": "Ferramentas e obra", "slug": "spray_paint_bottles", "dimensions": [0.42, 0.32, 0.26]},
    {"id": "work_light", "label": "Lâmpada de obra", "group": "Ferramentas e obra", "slug": "lightbulb_01", "dimensions": [0.12, 0.22, 0.12]},
    {"id": "plunger", "label": "Desentupidor", "group": "Banheiro", "slug": "plunger", "dimensions": [0.18, 0.55, 0.18]},
    {"id": "water_container", "label": "Galão de água", "group": "Cozinha e serviço", "slug": "plastic_bottle_gallon", "dimensions": [0.3, 0.48, 0.3]},
    {"id": "wall_clock", "label": "Relógio de parede", "group": "Decoração", "slug": "wall_clock", "dimensions": [0.42, 0.42, 0.08]},
]


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "my-home-local-assets/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "my-home-local-assets/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response, target.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_gltf_transform(arguments: list[str]) -> None:
    executable = shutil.which("npx")
    if not executable:
        raise RuntimeError("npx is required to package the downloaded glTF files")
    subprocess.run(
        [executable, "--yes", "@gltf-transform/cli", *arguments],
        cwd=ROOT,
        check=True,
    )


def package_polyhaven(asset: dict[str, Any], temporary: Path) -> dict[str, Any]:
    slug = asset["slug"]
    metadata = fetch_json(f"{POLYHAVEN_API}/info/{slug}")
    output = OUTPUT / f"{asset['id']}.glb"
    if not output.is_file():
        files = fetch_json(f"{POLYHAVEN_API}/files/{slug}")
        entry = files["gltf"]["1k"]["gltf"]
        source_dir = temporary / slug
        source = source_dir / f"{slug}.gltf"
        download(entry["url"], source)
        for relative, included in entry.get("include", {}).items():
            download(included["url"], source_dir / relative)
        run_gltf_transform(
            [
                "optimize",
                str(source),
                str(output),
                "--compress",
                "false",
                "--texture-size",
                "512",
                "--simplify",
                "true",
                "--simplify-ratio",
                str(asset.get("simplify_ratio", 0.65)),
                "--simplify-error",
                "0.002",
                "--palette",
                "false",
            ]
        )
    thumbnail = OUTPUT / "previews" / f"{asset['id']}.png"
    thumbnail_url = metadata.get("thumbnail_url")
    if thumbnail_url and not thumbnail.is_file():
        download(thumbnail_url, thumbnail)
    return {
        "source_url": f"https://polyhaven.com/a/{slug}",
        "author": ", ".join((metadata.get("authors") or {}).keys()) or "Poly Haven contributors",
        "license": "CC0-1.0",
        "source_resolution": "1k glTF",
        "source_slug": slug,
    }


def package_direct(asset: dict[str, Any]) -> dict[str, Any]:
    output = OUTPUT / f"{asset['id']}.glb"
    if not output.is_file():
        download(asset["direct_url"], output)
    preview = OUTPUT / "previews" / f"{asset['id']}.jpg"
    if asset.get("direct_preview_url") and not preview.is_file():
        download(
            asset["direct_preview_url"],
            preview,
        )
    return {
        "source_url": asset["source_url"],
        "author": asset["author"],
        "license": asset["license"],
        "source_resolution": "repository GLB",
    }


def write_generated_files(assets: list[dict[str, Any]]) -> None:
    catalog = {
        asset["id"]: {
            "label": asset["label"],
            "group": asset["group"],
            "width": asset["width_m"],
            "depth": asset["depth_m"],
            "height": asset["height_m"],
            "color": asset["color"],
            "modelUrl": asset["model_url"],
            "previewUrl": asset["preview_url"],
        }
        for asset in assets
    }
    (OUTPUT / "asset-catalog.js").write_text(
        "/* Generated by python/download_3d_assets.py. */\n"
        "export const LOCAL_ASSET_CATALOG = "
        + json.dumps(catalog, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    lines = [
        "# Third-party 3D assets",
        "",
        "All models are stored locally and do not require runtime network access.",
        "",
        "| Asset | Author | License | Source |",
        "| --- | --- | --- | --- |",
    ]
    for asset in assets:
        lines.append(
            f"| {asset['label']} | {asset['author']} | {asset['license']} | "
            f"[source]({asset['source_url']}) |"
        )
    (OUTPUT / "THIRD_PARTY_ASSETS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "previews").mkdir(parents=True, exist_ok=True)
    manifest_assets = []
    with tempfile.TemporaryDirectory(prefix="my-home-assets-") as folder:
        temporary = Path(folder)
        for asset in ASSETS:
            print(f"Packaging {asset['label']}...")
            provenance = (
                package_direct(asset)
                if asset.get("direct_url")
                else package_polyhaven(asset, temporary)
            )
            output = OUTPUT / f"{asset['id']}.glb"
            width, height, depth = asset["dimensions"]
            manifest_assets.append(
                {
                    "id": asset["id"],
                    "label": asset["label"],
                    "group": asset["group"],
                    "model_url": f"/assets/models/{asset['id']}.glb",
                    "preview_url": (
                        f"/assets/models/previews/{asset['id']}.png"
                        if (OUTPUT / "previews" / f"{asset['id']}.png").is_file()
                        else (
                            f"/assets/models/previews/{asset['id']}.jpg"
                            if (
                                OUTPUT / "previews" / f"{asset['id']}.jpg"
                            ).is_file()
                            else ""
                        )
                    ),
                    "width_m": width,
                    "height_m": height,
                    "depth_m": depth,
                    "color": asset.get("color")
                    or GROUP_COLORS.get(asset["group"], "#a87945"),
                    "bytes": output.stat().st_size,
                    "sha256": sha256(output),
                    **provenance,
                }
            )
    manifest = {
        "version": 1,
        "generated_by": "python/download_3d_assets.py",
        "runtime_network_required": False,
        "assets": manifest_assets,
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_generated_files(manifest_assets)
    print(f"Wrote {len(manifest_assets)} assets to {OUTPUT}")


if __name__ == "__main__":
    main()
