"""
Reference thresholds for deterministic dispensing parameter checks.

This module compares user-provided numeric process values against a small
Supabase table instead of asking the LLM to invent acceptable ranges.
"""

import re
from decimal import Decimal


PARAMETERS = {
    "volume": {
        "aliases": ["volume", "dispensing volume", "dispense volume"],
        "columns": ("min_volume", "target_volume", "max_volume"),
    },
    "pressure": {
        "aliases": ["pressure", "dispensing pressure"],
        "columns": ("min_pressure", "target_pressure", "max_pressure"),
    },
    "speed": {
        "aliases": ["speed", "flow rate", "dispensing speed"],
        "columns": ("min_speed", "target_speed", "max_speed"),
    },
    "time": {
        "aliases": ["time", "dispensing time", "dispense time"],
        "columns": ("min_time", "target_time", "max_time"),
    },
    "nozzle_size": {
        "aliases": ["nozzle", "nozzle size", "nozzle diameter"],
        "columns": ("min_nozzle_size", "target_nozzle_size", "max_nozzle_size"),
    },
    "height": {
        "aliases": ["height", "dispensing height", "dispense height"],
        "columns": ("min_height", "target_height", "max_height"),
    },
    "diameter": {
        "aliases": ["diameter", "dot diameter", "dot size"],
        "columns": (
            "min_diameter_mm",
            "target_diameter_mm",
            "max_diameter_mm",
        ),
    },
}


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _collect_case_text(problem_description: str, qa_pairs: list[dict]) -> str:
    parts = [problem_description or ""]
    for qa in qa_pairs or []:
        parts.append(qa.get("question", ""))
        parts.append(qa.get("answer", ""))
    return "\n".join(parts)


def _extract_measurements(text: str) -> dict[str, Decimal]:
    measurements = {}
    normalized = text.lower()

    for parameter, config in PARAMETERS.items():
        candidates = []
        if parameter == "diameter":
            for value_match in re.finditer(r"(\d+(?:\.\d+)?)\s*mm\b", normalized):
                candidates.append((value_match.start(), value_match.group(1)))

        for alias in config["aliases"]:
            for alias_match in re.finditer(re.escape(alias), normalized):
                after = normalized[alias_match.end():alias_match.end() + 60].split("\n", 1)[0]
                for value_match in re.finditer(r"\d+(?:\.\d+)?", after):
                    candidates.append(
                        (alias_match.end() + value_match.start(), value_match.group())
                    )

                before_start = max(0, alias_match.start() - 30)
                before = normalized[before_start:alias_match.start()].split("\n")[-1]
                before_values = list(re.finditer(r"\d+(?:\.\d+)?", before))
                if before_values:
                    value_match = before_values[-1]
                    candidates.append(
                        (before_start + value_match.start(), value_match.group())
                    )

        if candidates:
            _, latest_value = max(candidates, key=lambda candidate: candidate[0])
            measurements[parameter] = Decimal(latest_value)

    return measurements


def _score_row(
    row: dict,
    text: str,
    defect_type: str | None,
    measured_parameters: set[str],
) -> int:
    score = 0
    material = (row.get("material") or "").lower()
    row_defect_type = (row.get("defect_type") or "").lower()

    if material and material in text:
        score += 3
    elif material.startswith("generic"):
        score += 1
    if defect_type and row_defect_type == defect_type.lower():
        score += 2

    for parameter in measured_parameters:
        min_col, _, max_col = PARAMETERS[parameter]["columns"]
        if row.get(min_col) is not None and row.get(max_col) is not None:
            score += 2

    return score


async def get_best_threshold_row(
    problem_description: str,
    qa_pairs: list[dict],
    defect_type: str | None = None,
    project_id: int | None = None,
    knowledge_pack_id: int | None = None,
) -> dict | None:
    """Fetch the best matching threshold row for the current case."""
    from db.supabase_client import get_client

    client = get_client()
    query = client.table("reference_thresholds").select("*")
    if project_id is not None:
        query = query.eq("project_id", project_id)
    if knowledge_pack_id is not None:
        query = query.eq("knowledge_pack_id", knowledge_pack_id)

    result = query.execute()
    rows = result.data or []
    if not rows:
        return None

    text = _collect_case_text(problem_description, qa_pairs).lower()
    measured_parameters = set(_extract_measurements(text))
    scored_rows = [
        (
            _score_row(row, text, defect_type, measured_parameters),
            row,
        )
        for row in rows
    ]
    best_score, best_row = max(scored_rows, key=lambda item: item[0])
    return best_row if best_score > 0 else None


async def evaluate_reference_thresholds(
    problem_description: str,
    qa_pairs: list[dict],
    defect_type: str | None = None,
    project_id: int | None = None,
    knowledge_pack_id: int | None = None,
) -> dict:
    """
    Compare extracted numeric values against the best matching threshold row.
    """
    case_text = _collect_case_text(problem_description, qa_pairs)
    measurements = _extract_measurements(case_text)
    threshold_row = await get_best_threshold_row(
        problem_description=problem_description,
        qa_pairs=qa_pairs,
        defect_type=defect_type,
        project_id=project_id,
        knowledge_pack_id=knowledge_pack_id,
    )

    if not measurements or not threshold_row:
        return {"checks": [], "threshold_row": threshold_row}

    checks = []
    for parameter, measured_value in measurements.items():
        min_col, target_col, max_col = PARAMETERS[parameter]["columns"]
        min_value = _to_decimal(threshold_row.get(min_col))
        target_value = _to_decimal(threshold_row.get(target_col))
        max_value = _to_decimal(threshold_row.get(max_col))

        if min_value is None or max_value is None:
            continue

        if measured_value < min_value:
            status = "below_min"
            interpretation = "Measured value is below the acceptable minimum."
        elif measured_value > max_value:
            status = "above_max"
            interpretation = "Measured value is above the acceptable maximum."
        else:
            status = "pass"
            interpretation = "Measured value is within the acceptable range."

        checks.append(
            {
                "parameter": parameter,
                "measured": float(measured_value),
                "min": float(min_value),
                "target": float(target_value) if target_value is not None else None,
                "max": float(max_value),
                "status": status,
                "interpretation": interpretation,
            }
        )

    return {"checks": checks, "threshold_row": threshold_row}


def format_threshold_context(evaluation: dict) -> str:
    """Format threshold checks for injection into an agent prompt."""
    checks = evaluation.get("checks") or []
    row = evaluation.get("threshold_row") or {}
    if not checks:
        return ""

    lines = [
        "Reference Threshold Checks:",
        f"- Matched material: {row.get('material') or 'unspecified'}",
        f"- Matched defect type: {row.get('defect_type') or 'generic'}",
    ]

    for check in checks:
        lines.append(
            "- {parameter}: measured {measured}, acceptable {min} to {max}, "
            "target {target}, status {status}. {interpretation}".format(**check)
        )

    return "\n".join(lines)
