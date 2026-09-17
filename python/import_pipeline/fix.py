"""Build AI companion fix files for the ping-pong correction loop."""

from __future__ import annotations

from typing import Any


def build_fix_text(
    *,
    pack_name: str,
    file_name: str,
    primary_error: str,
    extra_notes: list[str] | None = None,
    headers: list[str] | None = None,
    rejected_text: str = "",
    user_instructions: str = "",
    expense_context: str = "",
) -> str:
    notes = extra_notes or []
    header_line = ",".join(headers or [])
    lines = [
        f"The importer rejected my last {pack_name}.",
        "",
        "IMPORT ERROR",
        primary_error.strip() or "unknown error",
        "",
        "EXTRA NOTES",
    ]
    if notes:
        lines.extend(f"- {n}" for n in notes)
    else:
        lines.append("- (none)")
    if expense_context.strip():
        lines.extend(["", "EXPENSE CONTEXT", expense_context.strip()])
    if user_instructions.strip():
        lines.extend(
            ["", "ADDITIONAL HUMAN INSTRUCTIONS", user_instructions.strip()]
        )
    lines.extend(
        [
            "",
            "WHAT YOU MUST DO",
            f"- Re-emit a COMPLETE {pack_name} pack with correct markers.",
            f"- Include ===FILE: {file_name}=== with header:",
            f"  {header_line}",
            "- Each data row must include unit_price and id (preferred) or description.",
            "- Repair only from the supplied quotation evidence; do not browse or invent values.",
            "- Preserve source_type, source_name, source_page, confidence, and ambiguities.",
            "- Do not claim you wrote files to disk.",
            "",
            "DELIVERY RULES",
            f"- Save/overwrite exactly as {pack_name} (no updated/corrected/v2 suffixes).",
            "- Keep ===PREVIEW=== / ===END_PREVIEW=== and ===FILE=== / ===END_FILE=== markers.",
            "- Return the full pack, not a partial patch.",
            "",
            f"I will paste/upload {pack_name} and re-import.",
        ]
    )
    if rejected_text.strip():
        lines.extend(
            [
                "",
                "REJECTED RESPONSE FOR REPAIR",
                rejected_text.strip(),
            ]
        )
    return "\n".join(lines) + "\n"
