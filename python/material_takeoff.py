"""House takeoff → material quantities, median prices, budget forecast."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

from expense_store import ExpenseStore, now_stamp  # noqa: E402
from persistence import atomic_write_text, timestamp  # noqa: E402

DATA_DIR = ROOT / "data"
HOUSE_PATH = DATA_DIR / "house.json"
RATES_PATH = DATA_DIR / "takeoff-rates.json"
FORECAST_JSON = DATA_DIR / "budget-forecast.json"
FORECAST_MD = DATA_DIR / "budget-forecast.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[mid], 4)
    return round((ordered[mid - 1] + ordered[mid]) / 2, 4)


def _room_dims(room: dict[str, Any]) -> tuple[float, float]:
    measured = room.get("measured_walls_meters") or {}
    if isinstance(measured, dict):
        width = measured.get("width")
        depth = measured.get("depth")
        if width and depth:
            return float(width), float(depth)
        nums = [
            float(value)
            for key, value in measured.items()
            if key in {"width", "depth", "top", "bottom", "left", "right"}
            and value not in {None, ""}
        ]
        if len(nums) >= 2:
            return nums[0], nums[1]
    area = float(room.get("approx_area_m2") or 0)
    if area > 0:
        side = math.sqrt(area)
        return side, side
    return 0.0, 0.0


def derive_measurements(house: dict[str, Any], rates: dict[str, Any]) -> dict[str, Any]:
    settings = rates.get("measurements") or {}
    wall_height = float(settings.get("wall_height_m") or 2.7)
    rooms = house.get("interior_rooms") or []
    floor_area = float(house.get("interior_useful_area_m2") or 0)
    if floor_area <= 0:
        floor_area = sum(float(room.get("approx_area_m2") or 0) for room in rooms)

    wall_area = 0.0
    opening_area = 0.0
    interior_door_count = 0
    window_count = 0
    for room in rooms:
        if not isinstance(room, dict):
            continue
        width, depth = _room_dims(room)
        if width > 0 and depth > 0:
            wall_area += 2 * (width + depth) * wall_height
        kind = str(room.get("kind") or "")
        if kind not in {"circulation"}:
            interior_door_count += 1
        for opening in room.get("openings") or []:
            if not isinstance(opening, dict):
                continue
            otype = str(opening.get("type") or "")
            if otype == "window":
                window_count += 1
                ow = float(opening.get("width_m") or 0)
                oh = float(opening.get("height_m") or 0)
                opening_area += ow * oh
            elif otype == "door":
                ow = float(opening.get("width_m") or 0.8)
                oh = float(opening.get("height_m") or 2.1)
                opening_area += ow * oh

    net_wall_area = max(0.0, wall_area - opening_area)
    model = house.get("model_3d") or {}
    building = model.get("building") or {}
    footprint = float(building.get("width_m") or 0) * float(
        building.get("depth_m") or 0
    )
    if footprint <= 0:
        footprint = floor_area

    room_count = sum(
        1
        for room in rooms
        if isinstance(room, dict) and str(room.get("kind") or "") != "circulation"
    )

    return {
        "floor_area_m2": round(floor_area, 4),
        "wall_area_gross_m2": round(wall_area, 4),
        "wall_area_net_m2": round(net_wall_area, 4),
        "opening_area_m2": round(opening_area, 4),
        "building_footprint_m2": round(footprint, 4),
        "interior_door_count": interior_door_count,
        "window_count": window_count,
        "habitable_room_count": room_count,
        "wall_height_m": wall_height,
        "gantt_porcelain_scope_m2": float(
            settings.get("gantt_porcelain_scope_m2") or 0
        ),
    }


def compute_quantity(
    expense_id: str,
    rule: dict[str, Any],
    measurements: dict[str, Any],
    settings: dict[str, Any],
) -> tuple[float, str]:
    method = str(rule.get("method") or "fixed_units")
    if method == "fixed_units":
        return float(rule.get("quantity") or 1), "fixed_units"

    floor = float(measurements["floor_area_m2"])
    if method == "porcelain_floor":
        gantt = float(measurements.get("gantt_porcelain_scope_m2") or 0)
        waste = float(settings.get("porcelain_waste_factor") or 1.1)
        base = gantt if gantt > 0 else floor * waste
        if gantt > 0:
            return round(gantt, 4), "gantt_porcelain_scope_m2"
        return round(base, 4), "floor_area_m2 × waste"

    if method == "grout_from_floor":
        porcelain, _ = compute_quantity(
            "EXP_0023",
            {"method": "porcelain_floor"},
            measurements,
            settings,
        )
        return (
            round(porcelain * float(settings.get("grout_kg_per_m2") or 1.2), 4),
            "porcelain×grout",
        )

    if method == "mortar_from_floor":
        porcelain, _ = compute_quantity(
            "EXP_0023",
            {"method": "porcelain_floor"},
            measurements,
            settings,
        )
        return (
            round(porcelain * float(settings.get("mortar_bags_per_m2") or 0.35), 4),
            "porcelain×mortar",
        )

    if method == "interior_doors":
        count = int(measurements.get("interior_door_count") or 5)
        return float(max(count, 1)), "interior_door_count"

    if method == "conduit_from_floor":
        return (
            round(floor * float(settings.get("conduit_m_per_m2_floor") or 2.5), 4),
            "floor×conduit",
        )

    if method == "lamps_from_rooms":
        rooms = int(measurements.get("habitable_room_count") or 1)
        return float(rooms * int(settings.get("lamps_per_room") or 2)), "rooms×lamps"

    if method == "outlets_from_rooms":
        rooms = int(measurements.get("habitable_room_count") or 1)
        return (
            float(rooms * int(settings.get("outlets_per_room") or 4)),
            "rooms×outlets",
        )

    if method == "baseboard_from_floor":
        # Approximate rectangular perimeter from area
        side = math.sqrt(max(floor, 0.01))
        perimeter = 4 * side
        return (
            round(
                perimeter * float(settings.get("baseboard_factor_of_perimeter") or 1), 4
            ),
            "approx_perimeter",
        )

    if method == "roof_framing_area":
        return (
            round(float(measurements["building_footprint_m2"]), 4),
            "building_footprint",
        )

    if method == "roof_tiles":
        area = float(measurements["building_footprint_m2"])
        per_m2 = float(settings.get("roof_tile_per_m2") or 16)
        return round(area * per_m2 * 1.08, 4), "footprint×tiles×waste"

    if method == "paint_cans":
        wall = float(measurements["wall_area_net_m2"])
        liters_needed = wall / float(settings.get("paint_effective_m2_per_liter") or 6)
        cans = math.ceil(liters_needed / float(settings.get("paint_can_liters") or 18))
        return float(max(cans, 1)), "wall_net / coverage -> cans"

    if method == "tarp_from_floor":
        return (
            round(floor * float(settings.get("tarp_coverage_factor") or 1.2), 4),
            "floor×tarp_factor",
        )

    return float(rule.get("quantity") or 1), "fallback_fixed"


def median_unit_price(expense: dict[str, Any]) -> float | None:
    prices = [
        float(quote["unit_price"])
        for quote in expense.get("quotations") or []
        if not quote.get("archived")
        and quote.get("unit_price") is not None
        and math.isfinite(float(quote.get("unit_price") or 0))
    ]
    return _median(prices)


def build_forecast(
    store: ExpenseStore,
    house: dict[str, Any],
    rates: dict[str, Any],
) -> dict[str, Any]:
    settings = rates.get("measurements") or {}
    materials_rules = rates.get("materials") or {}
    measurements = derive_measurements(house, rates)
    expenses = store.list_expenses()
    lines: list[dict[str, Any]] = []
    materials_total = 0.0
    services_total = 0.0

    for expense in expenses:
        expense_id = expense["id"]
        record_type = expense.get("record_type") or "service"
        if record_type == "material":
            rule = materials_rules.get(expense_id) or {
                "method": "fixed_units",
                "quantity": expense.get("default_expected_quantity") or 1,
                "confidence": "estimated",
                "formula_notes": "No takeoff rule; kept previous default.",
            }
            quantity, basis = compute_quantity(expense_id, rule, measurements, settings)
            median = median_unit_price(expense)
            unit_price = median
            if unit_price is None and expense.get("unit_price") is not None:
                unit_price = float(expense["unit_price"])
            line_total = (
                round(quantity * float(unit_price), 2)
                if unit_price is not None
                else None
            )
            if line_total is not None:
                materials_total += line_total
            lines.append(
                {
                    "expense_id": expense_id,
                    "description": expense["description"],
                    "record_type": "material",
                    "cost_class": "variable_material",
                    "unit": expense.get("unit") or "",
                    "quantity": quantity,
                    "quantity_basis": basis,
                    "confidence": rule.get("confidence") or "estimated",
                    "formula_notes": rule.get("formula_notes") or "",
                    "median_unit_price": median,
                    "unit_price_used": unit_price,
                    "forecast_total": line_total,
                    "planned_total": expense.get("value"),
                }
            )
        else:
            planned = float(expense.get("value") or 0)
            services_total += planned
            lines.append(
                {
                    "expense_id": expense_id,
                    "description": expense["description"],
                    "record_type": "service",
                    "cost_class": "fixed_one_time",
                    "unit": expense.get("unit") or "",
                    "quantity": 1,
                    "quantity_basis": "fixed_service",
                    "confidence": "measured",
                    "formula_notes": "One-time / service expense; not takeoff-driven.",
                    "median_unit_price": median_unit_price(expense),
                    "unit_price_used": expense.get("unit_price"),
                    "forecast_total": round(planned, 2),
                    "planned_total": planned,
                }
            )

    return {
        "version": 1,
        "generated_at": timestamp(),
        "location_basis": rates.get("location_basis") or "nova_odessa_cep_13380",
        "assumptions": rates.get("assumptions") or [],
        "measurements": measurements,
        "summary": {
            "forecast_all": round(materials_total + services_total, 2),
            "forecast_materials": round(materials_total, 2),
            "forecast_services": round(services_total, 2),
            "material_lines": sum(
                1 for line in lines if line["record_type"] == "material"
            ),
            "service_lines": sum(
                1 for line in lines if line["record_type"] == "service"
            ),
        },
        "lines": lines,
    }


def apply_quantities(store: ExpenseStore, forecast: dict[str, Any]) -> int:
    qty_by_id = {
        str(line["expense_id"]): float(line["quantity"])
        for line in forecast.get("lines") or []
        if line.get("record_type") == "material"
    }
    rows = store._read_rows()
    stamp = now_stamp()
    updated = 0
    for row in rows:
        expense_id = str(row.get("id") or "")
        if expense_id not in qty_by_id:
            continue
        quantity = f"{qty_by_id[expense_id]:g}"
        if row.get("default_expected_quantity") == quantity:
            continue
        row["default_expected_quantity"] = quantity
        row["updated_at"] = stamp
        updated += 1
    if updated:
        store._write_rows(rows)
    return updated


def write_markdown(forecast: dict[str, Any]) -> str:
    summary = forecast["summary"]
    lines = [
        "# Orçamento projetado (takeoff × mediana)",
        "",
        f"Gerado em: {forecast['generated_at']}",
        "",
        f"- **Projetado total:** R$ {summary['forecast_all']:,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        f"- Materiais: R$ {summary['forecast_materials']:,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        f"- Serviços / taxas únicas: R$ {summary['forecast_services']:,.2f}".replace(
            ",", "X"
        )
        .replace(".", ",")
        .replace("X", "."),
        "",
        "## Medidas derivadas",
        "",
    ]
    for key, value in (forecast.get("measurements") or {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Premissas", ""])
    for note in forecast.get("assumptions") or []:
        lines.append(f"- {note}")
    lines.extend(["", "## Linhas (materiais por custo projetado)", ""])
    material_lines = sorted(
        [
            line
            for line in forecast.get("lines") or []
            if line.get("record_type") == "material"
            and line.get("forecast_total") is not None
        ],
        key=lambda item: float(item["forecast_total"]),
        reverse=True,
    )
    for line in material_lines[:25]:
        lines.append(
            f"- **{line['description']}**: qtd {line['quantity']} × "
            f"R$ {float(line['unit_price_used'] or 0):.2f} = "
            f"R$ {float(line['forecast_total']):.2f} "
            f"({line.get('confidence')}; {line.get('quantity_basis')})"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute forecast without writing expense quantities.",
    )
    args = parser.parse_args()
    house = _read_json(HOUSE_PATH)
    rates = _read_json(RATES_PATH)
    store = ExpenseStore(DATA_DIR)
    forecast = build_forecast(store, house, rates)
    if not args.dry_run:
        updated = apply_quantities(store, forecast)
        # Rebuild forecast after quantity write so planned totals refresh
        forecast = build_forecast(store, house, rates)
        forecast["quantities_written"] = updated
    else:
        forecast["quantities_written"] = 0

    atomic_write_text(
        FORECAST_JSON,
        json.dumps(forecast, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(FORECAST_MD, write_markdown(forecast))
    summary = forecast["summary"]
    print(
        f"Forecast R$ {summary['forecast_all']:.2f} "
        f"(materials {summary['forecast_materials']:.2f} + "
        f"services {summary['forecast_services']:.2f}); "
        f"wrote {forecast.get('quantities_written', 0)} material quantities; "
        f"dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
