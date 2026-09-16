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
    files = fetch_json(f"{POLYHAVEN_API}/files/{slug}")
    metadata = fetch_json(f"{POLYHAVEN_API}/info/{slug}")
    entry = files["gltf"]["1k"]["gltf"]
    source_dir = temporary / slug
    source = source_dir / f"{slug}.gltf"
    download(entry["url"], source)
    for relative, included in entry.get("include", {}).items():
        download(included["url"], source_dir / relative)
    output = OUTPUT / f"{asset['id']}.glb"
    if asset.get("simplify_ratio"):
        copied = temporary / f"{slug}.glb"
        run_gltf_transform(["copy", str(source), str(copied)])
        run_gltf_transform(["weld", str(copied), str(copied)])
        run_gltf_transform(
            [
                "simplify",
                str(copied),
                str(output),
                "--ratio",
                str(asset["simplify_ratio"]),
                "--error",
                "0.02",
            ]
        )
    else:
        run_gltf_transform(["copy", str(source), str(output)])
    thumbnail = OUTPUT / "previews" / f"{asset['id']}.png"
    thumbnail_url = metadata.get("thumbnail_url")
    if thumbnail_url:
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
    download(asset["direct_url"], output)
    if asset.get("direct_preview_url"):
        download(
            asset["direct_preview_url"],
            OUTPUT / "previews" / f"{asset['id']}.jpg",
        )
    return {
        "source_url": asset["source_url"],
        "author": asset["author"],
        "license": asset["license"],
        "source_resolution": "repository GLB",
    }


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
    print(f"Wrote {len(manifest_assets)} assets to {OUTPUT}")


if __name__ == "__main__":
    main()
