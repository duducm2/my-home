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
GLTF_TRANSFORM_VERSION = "4.5.0"
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
    "Limpeza e lavanderia": "#72a8a1",
    "Segurança e acesso": "#b95f5f",
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
    {"id": "armchair", "label": "Poltrona", "group": "Sala", "slug": "ArmChair_01", "dimensions": [0.85, 0.95, 0.85], "keywords": "assento sala leitura"},
    {"id": "ottoman", "label": "Puff", "group": "Sala", "slug": "Ottoman_01", "dimensions": [0.65, 0.45, 0.65], "keywords": "apoio pés assento"},
    {"id": "side_table", "label": "Mesa lateral", "group": "Sala", "slug": "WoodenTable_02", "dimensions": [0.55, 0.58, 0.55], "keywords": "mesa apoio canto"},
    {"id": "floor_lamp", "label": "Luminária de piso", "group": "Iluminação", "slug": "industrial_pipe_lamp", "dimensions": [0.42, 1.55, 0.42], "keywords": "abajur luz sala"},
    {"id": "tv_console", "label": "Rack de TV", "group": "Sala", "slug": "ClassicConsole_01", "dimensions": [1.65, 0.62, 0.42], "keywords": "painel televisão console"},
    {"id": "room_divider", "label": "Biombo", "group": "Decoração", "slug": "chinese_screen_panels", "dimensions": [1.8, 1.8, 0.12], "keywords": "divisória painel"},
    {"id": "rocking_chair", "label": "Cadeira de balanço", "group": "Sala", "slug": "Rockingchair_01", "dimensions": [0.72, 1.05, 1.0], "keywords": "poltrona descanso"},
    {"id": "game_console", "label": "Console de jogos", "group": "Sala", "slug": "gaming_console", "dimensions": [0.32, 0.1, 0.26], "keywords": "videogame eletrônico tv"},
    {"id": "projector_screen", "label": "Tela de projeção", "group": "Sala", "slug": "projector_screen", "dimensions": [2.0, 1.3, 0.1], "keywords": "cinema projetor painel"},
    {"id": "radio", "label": "Caixa de som", "group": "Sala", "slug": "boombox", "dimensions": [0.5, 0.28, 0.2], "keywords": "rádio música áudio"},
    {"id": "ceramic_vase", "label": "Vaso decorativo", "group": "Decoração", "slug": "ceramic_vase_01", "dimensions": [0.28, 0.45, 0.28], "keywords": "cerâmica enfeite"},
    {"id": "planter_box", "label": "Floreira", "group": "Exterior", "slug": "planter_box_01", "dimensions": [0.9, 0.42, 0.36], "keywords": "jardim plantas vaso"},
    {"id": "bedroom_stool", "label": "Banqueta de quarto", "group": "Quarto", "slug": "chinese_stool", "dimensions": [0.42, 0.48, 0.42], "keywords": "penteadeira assento"},
    {"id": "storage_chest", "label": "Baú", "group": "Quarto", "slug": "treasure_chest", "dimensions": [0.9, 0.55, 0.52], "keywords": "armazenamento roupas"},
    {"id": "suitcase", "label": "Mala", "group": "Quarto", "slug": "vintage_suitcase", "dimensions": [0.72, 0.22, 0.5], "keywords": "bagagem armazenamento"},
    {"id": "laundry_basket", "label": "Cesto de roupas", "group": "Limpeza e lavanderia", "slug": "wicker_basket_01", "dimensions": [0.45, 0.6, 0.45], "keywords": "lavanderia roupa suja"},
    {"id": "alarm_clock", "label": "Despertador", "group": "Quarto", "slug": "alarm_clock_01", "dimensions": [0.18, 0.16, 0.1], "keywords": "relógio criado mudo"},
    {"id": "candleholders", "label": "Castiçais", "group": "Decoração", "slug": "brass_candleholders", "dimensions": [0.4, 0.48, 0.18], "keywords": "velas iluminação enfeite"},
    {"id": "laptop", "label": "Notebook", "group": "Escritório", "slug": "classic_laptop", "dimensions": [0.36, 0.24, 0.26], "keywords": "computador trabalho"},
    {"id": "clipboard", "label": "Prancheta", "group": "Escritório", "slug": "clipboard", "dimensions": [0.24, 0.02, 0.34], "keywords": "documentos papel"},
    {"id": "stationery_set", "label": "Material de escritório", "group": "Escritório", "slug": "stationery_supplies", "dimensions": [0.42, 0.18, 0.3], "keywords": "canetas lápis papel"},
    {"id": "notepads", "label": "Cadernos", "group": "Escritório", "slug": "office_notepads", "dimensions": [0.32, 0.08, 0.24], "keywords": "bloco notas papel"},
    {"id": "stapler", "label": "Grampeador", "group": "Escritório", "slug": "vintage_stapler", "dimensions": [0.2, 0.1, 0.07], "keywords": "papel material"},
    {"id": "magnifier", "label": "Lupa", "group": "Escritório", "slug": "magnifying_glass_01", "dimensions": [0.12, 0.03, 0.28], "keywords": "leitura ferramenta"},
    {"id": "chalkboard", "label": "Quadro de anotações", "group": "Escritório", "slug": "standing_chalkboard_01", "dimensions": [0.7, 1.25, 0.45], "keywords": "lousa recados"},
    {"id": "circuit_board", "label": "Equipamento eletrônico", "group": "Escritório", "slug": "circuit_board", "dimensions": [0.28, 0.04, 0.2], "keywords": "computador placa manutenção"},
    {"id": "all_purpose_cleaner", "label": "Limpador multiuso", "group": "Limpeza e lavanderia", "slug": "all_purpose_cleaner", "dimensions": [0.12, 0.3, 0.1], "keywords": "produto limpeza"},
    {"id": "bleach", "label": "Água sanitária", "group": "Limpeza e lavanderia", "slug": "bleach_bottle", "dimensions": [0.14, 0.32, 0.11], "keywords": "produto limpeza lavanderia"},
    {"id": "drain_cleaner", "label": "Limpador de ralo", "group": "Limpeza e lavanderia", "slug": "drain_cleaner", "dimensions": [0.1, 0.28, 0.1], "keywords": "banheiro encanamento"},
    {"id": "dustpan", "label": "Pá de lixo", "group": "Limpeza e lavanderia", "slug": "dustpan", "dimensions": [0.3, 0.12, 0.28], "keywords": "varrer limpeza"},
    {"id": "broom", "label": "Vassoura", "group": "Limpeza e lavanderia", "slug": "plastic_broom", "dimensions": [0.3, 1.35, 0.12], "keywords": "varrer limpeza"},
    {"id": "utility_bucket", "label": "Balde", "group": "Limpeza e lavanderia", "slug": "wooden_bucket_01", "dimensions": [0.34, 0.38, 0.34], "keywords": "água limpeza obra"},
    {"id": "plastic_bin", "label": "Caixa organizadora", "group": "Limpeza e lavanderia", "slug": "plastic_container", "dimensions": [0.6, 0.38, 0.42], "keywords": "armazenamento caixa"},
    {"id": "trash_bag", "label": "Saco de lixo", "group": "Limpeza e lavanderia", "slug": "trashbag", "dimensions": [0.45, 0.72, 0.38], "keywords": "resíduo entulho"},
    {"id": "rubber_boots", "label": "Botas de borracha", "group": "Limpeza e lavanderia", "slug": "rubber_boots", "dimensions": [0.42, 0.46, 0.32], "keywords": "epi chuva obra"},
    {"id": "cleaner_tin", "label": "Produto de manutenção", "group": "Limpeza e lavanderia", "slug": "cleaner_tin_01", "dimensions": [0.14, 0.22, 0.14], "keywords": "limpeza lata"},
    {"id": "bar_stool", "label": "Banqueta alta", "group": "Cozinha e serviço", "slug": "bar_chair_round_01", "dimensions": [0.42, 0.78, 0.42], "keywords": "ilha cozinha gourmet"},
    {"id": "propane_tank", "label": "Botijão de gás", "group": "Cozinha e serviço", "slug": "propane_tank", "dimensions": [0.38, 0.72, 0.38], "keywords": "glp cozinha"},
    {"id": "small_lpg_tank", "label": "Botijão de gás pequeno", "group": "Cozinha e serviço", "slug": "small_lpg_tank", "dimensions": [0.3, 0.48, 0.3], "keywords": "glp churrasqueira"},
    {"id": "cutting_board", "label": "Tábua de corte", "group": "Cozinha e serviço", "slug": "wooden_cutting_board", "dimensions": [0.42, 0.04, 0.28], "keywords": "utensílio cozinha"},
    {"id": "wooden_spoon", "label": "Colher de cozinha", "group": "Cozinha e serviço", "slug": "wooden_spoon", "dimensions": [0.08, 0.04, 0.32], "keywords": "utensílio"},
    {"id": "tea_set", "label": "Jogo de café", "group": "Cozinha e serviço", "slug": "tea_set_01", "dimensions": [0.55, 0.28, 0.4], "keywords": "xícara bule mesa"},
    {"id": "wine_bottles", "label": "Garrafas", "group": "Cozinha e serviço", "slug": "wine_bottles_01", "dimensions": [0.42, 0.34, 0.24], "keywords": "bebidas adega"},
    {"id": "water_jug", "label": "Jarra", "group": "Cozinha e serviço", "slug": "jug_01", "dimensions": [0.2, 0.32, 0.2], "keywords": "água cozinha mesa"},
    {"id": "covered_car", "label": "Carro coberto", "group": "Exterior", "slug": "covered_car", "dimensions": [4.5, 1.55, 1.9], "keywords": "garagem veículo", "simplify_ratio": 0.35},
    {"id": "security_camera", "label": "Câmera de segurança", "group": "Segurança e acesso", "slug": "security_camera_01", "dimensions": [0.22, 0.18, 0.38], "keywords": "cftv vigilância"},
    {"id": "fire_extinguisher", "label": "Extintor", "group": "Segurança e acesso", "slug": "korean_fire_extinguisher_01", "dimensions": [0.22, 0.65, 0.22], "keywords": "incêndio segurança"},
    {"id": "garden_hose", "label": "Mangueira de jardim", "group": "Exterior", "slug": "garden_hose_wall_mounted_01", "dimensions": [0.52, 0.52, 0.25], "keywords": "água quintal"},
    {"id": "sprinkler", "label": "Aspersor de jardim", "group": "Exterior", "slug": "garden_sprinkler_01", "dimensions": [0.45, 0.18, 0.38], "keywords": "irrigação água"},
    {"id": "garden_gloves", "label": "Luvas de jardinagem", "group": "Exterior", "slug": "garden_gloves_01", "dimensions": [0.3, 0.08, 0.24], "keywords": "epi jardim"},
    {"id": "watering_can", "label": "Regador", "group": "Exterior", "slug": "watering_can_metal_01", "dimensions": [0.55, 0.42, 0.3], "keywords": "plantas jardim água"},
    {"id": "garden_gnome", "label": "Enfeite de jardim", "group": "Exterior", "slug": "garden_gnome", "dimensions": [0.32, 0.72, 0.3], "keywords": "decoração quintal"},
    {"id": "adjustable_wrench", "label": "Chave inglesa", "group": "Ferramentas e obra", "slug": "adjustable_wrench", "dimensions": [0.08, 0.04, 0.32], "keywords": "ferramenta encanamento"},
    {"id": "bolt_cutters", "label": "Alicate corta-vergalhão", "group": "Ferramentas e obra", "slug": "bolt_cutters_01", "dimensions": [0.22, 0.08, 0.75], "keywords": "corte ferramenta"},
    {"id": "hammer", "label": "Martelo", "group": "Ferramentas e obra", "slug": "cross_pein_hammer", "dimensions": [0.32, 0.12, 0.1], "keywords": "prego ferramenta"},
    {"id": "crowbar", "label": "Pé de cabra", "group": "Ferramentas e obra", "slug": "crowbar_01", "dimensions": [0.08, 0.08, 0.85], "keywords": "demolição ferramenta"},
    {"id": "screwdriver", "label": "Chave de fenda", "group": "Ferramentas e obra", "slug": "flathead_screwdriver", "dimensions": [0.05, 0.05, 0.28], "keywords": "parafuso ferramenta"},
    {"id": "handsaw", "label": "Serrote", "group": "Ferramentas e obra", "slug": "handsaw_wood", "dimensions": [0.62, 0.18, 0.04], "keywords": "madeira corte"},
    {"id": "sledgehammer", "label": "Marreta", "group": "Ferramentas e obra", "slug": "sledgehammer_01", "dimensions": [0.85, 0.18, 0.12], "keywords": "demolição ferramenta"},
    {"id": "power_box", "label": "Caixa elétrica", "group": "Ferramentas e obra", "slug": "power_box_01", "dimensions": [0.55, 0.75, 0.22], "keywords": "quadro energia infraestrutura"},
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
        [
            executable,
            "--yes",
            f"@gltf-transform/cli@{GLTF_TRANSFORM_VERSION}",
            *arguments,
        ],
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
                str(asset.get("texture_size", 512)),
                "--simplify",
                "true",
                "--simplify-ratio",
                str(asset.get("simplify_ratio", 0.65)),
                "--simplify-error",
                str(asset.get("simplify_error", 0.002)),
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
            "keywords": asset.get("keywords", ""),
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
                    "keywords": asset.get("keywords", ""),
                    "bytes": output.stat().st_size,
                    "sha256": sha256(output),
                    **provenance,
                }
            )
    manifest = {
        "version": 2,
        "generated_by": "python/download_3d_assets.py",
        "runtime_network_required": False,
        "assets": manifest_assets,
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_generated_files(manifest_assets)
    expected_models = {f"{asset['id']}.glb" for asset in ASSETS}
    orphaned_models = sorted(
        path.name
        for path in OUTPUT.glob("*.glb")
        if path.name not in expected_models
    )
    expected_previews = {asset["id"] for asset in ASSETS}
    orphaned_previews = sorted(
        path.name
        for path in (OUTPUT / "previews").glob("*")
        if path.is_file() and path.stem not in expected_previews
    )
    if orphaned_models or orphaned_previews:
        raise RuntimeError(
            "orphaned asset files detected: "
            + ", ".join(orphaned_models + orphaned_previews)
        )
    print(f"Wrote {len(manifest_assets)} assets to {OUTPUT}")


if __name__ == "__main__":
    main()
