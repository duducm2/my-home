"""Pack type registry for reusable import workflows."""

from __future__ import annotations

from typing import Any, Callable

PRICE_PACK = {
    "id": "price",
    "canonical_pack": "PRICE_PACK.txt",
    "file_name": "PRICE_PACK.csv",
    "fix_filename": "PRICE_AI_FIX.txt",
    "headers": [
        "id",
        "description",
        "quotation_id",
        "unit_price",
        "quantity",
        "unit",
        "vendor",
        "shipping_cost",
        "total_price",
        "product_url",
        "price_notes",
        "checked_at",
        "selected",
    ],
    "required_any": ["id", "description"],
    "required_price": ["unit_price"],
}

PACK_TYPES: dict[str, dict[str, Any]] = {
    "price": PRICE_PACK,
}


def get_pack_type(pack_id: str = "price") -> dict[str, Any]:
    if pack_id not in PACK_TYPES:
        raise ValueError(f"unknown pack type: {pack_id}")
    return PACK_TYPES[pack_id]
