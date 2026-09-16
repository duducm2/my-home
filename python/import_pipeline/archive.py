"""Archive successful import packs under data/imported/."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def archive_pack(data_dir: Path, pack_text: str, prefix: str = "PRICE_PACK") -> str:
    imported = data_dir / "imported"
    imported.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{prefix}-{stamp}.txt"
    path = imported / name
    path.write_text(pack_text, encoding="utf-8", newline="\n")
    return name
