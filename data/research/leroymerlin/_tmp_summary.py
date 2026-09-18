import json
from pathlib import Path

root = Path(r"C:\Users\eduev\Meu Drive\17 - Projects\my-home\data\research\leroymerlin")
verified = no_match = 0
for p in sorted(root.glob("cluster-*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    print("==", p.name, "==")
    for e in d["expenses"]:
        w = e.get("winner")
        if e["match_status"] == "verified" and w:
            verified += 1
            print(
                "  OK",
                e["expense_id"],
                f"R${w['normalized_unit_price_brl']:.2f}",
                "|",
                w["matched_product"][:70],
            )
        else:
            no_match += 1
            print(
                "  NO",
                e["expense_id"],
                e["requested_item"][:40],
                "| cand=",
                len(e.get("candidates") or []),
                "|",
                (e.get("no_match_reason") or "")[:90],
            )
print(f"TOTAL verified={verified} no_match={no_match}")
