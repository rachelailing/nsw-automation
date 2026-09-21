"""Retrieve structured, approved content for the active Knowledge Pack."""

from db.supabase_client import get_client


async def get_knowledge_content(
    knowledge_pack_id: int,
    defect_type: str | None = None,
) -> dict:
    """Return material facts, expert rules, and actions from one pack."""
    client = get_client()

    materials_result = (
        client.table("materials")
        .select(
            "id, source_id, name, aliases, material_type, viscosity_min, "
            "viscosity_max, viscosity_unit, handling_notes, storage_conditions"
        )
        .eq("knowledge_pack_id", knowledge_pack_id)
        .order("name")
        .execute()
    )

    rules_query = (
        client.table("defect_rules")
        .select(
            "id, source_id, defect_type, conditions, possible_cause, category, "
            "reasoning, evidence_weight"
        )
        .eq("knowledge_pack_id", knowledge_pack_id)
    )
    actions_query = (
        client.table("troubleshooting_actions")
        .select(
            "id, source_id, defect_type, cause, action, sequence, safety_notes, "
            "requires_approval"
        )
        .eq("knowledge_pack_id", knowledge_pack_id)
    )

    if defect_type:
        rules_query = rules_query.eq("defect_type", defect_type)
        actions_query = actions_query.eq("defect_type", defect_type)

    rules_result = rules_query.order("evidence_weight", desc=True).execute()
    actions_result = actions_query.order("sequence").execute()

    return {
        "materials": materials_result.data or [],
        "defect_rules": rules_result.data or [],
        "troubleshooting_actions": actions_result.data or [],
    }


def format_knowledge_context(content: dict | None) -> str:
    """Format structured pack records as concise model evidence."""
    if not content:
        return "No approved Knowledge Pack content was provided."

    lines = [
        "Approved Knowledge Pack Context",
        "Treat this as expert guidance, not proof that a cause is confirmed.",
    ]

    materials = content.get("materials") or []
    if materials:
        lines.append("\nMaterial facts:")
        for item in materials:
            viscosity = ""
            if item.get("viscosity_min") is not None or item.get("viscosity_max") is not None:
                viscosity = (
                    f"; viscosity {item.get('viscosity_min', '?')}-"
                    f"{item.get('viscosity_max', '?')} {item.get('viscosity_unit') or ''}"
                )
            lines.append(
                f"- [material:{item.get('id')}; source:{item.get('source_id')}] "
                f"{item.get('name')}{viscosity}. "
                f"Handling: {item.get('handling_notes') or 'Not specified'} "
                f"Storage: {item.get('storage_conditions') or 'Not specified'}"
            )

    rules = content.get("defect_rules") or []
    if rules:
        lines.append("\nExpert defect rules:")
        for rule in rules:
            lines.append(
                f"- [rule:{rule.get('id')}; source:{rule.get('source_id')}] "
                f"For {rule.get('defect_type')}, possible cause: "
                f"{rule.get('possible_cause')} ({rule.get('category')}); "
                f"conditions={rule.get('conditions') or {}}; "
                f"weight={rule.get('evidence_weight')}. "
                f"Reason: {rule.get('reasoning')}"
            )

    actions = content.get("troubleshooting_actions") or []
    if actions:
        lines.append("\nApproved troubleshooting actions:")
        for action in actions:
            approval = "; engineer approval required" if action.get("requires_approval") else ""
            safety = f"; safety: {action.get('safety_notes')}" if action.get("safety_notes") else ""
            lines.append(
                f"- [action:{action.get('id')}; source:{action.get('source_id')}] "
                f"Step {action.get('sequence')}: {action.get('action')} "
                f"Cause: {action.get('cause')}{approval}{safety}"
            )

    if len(lines) == 2:
        lines.append("\nThe active pack contains no structured content for this defect.")

    return "\n".join(lines)
