from db.supabase_client import get_client


async def save_case_feedback(
    case_id: int,
    session_id: str,
    fixed: bool,
    attempted_action: str,
    confirmed_cause: str | None,
) -> dict:
    client = get_client()

    data = {
        "case_id": case_id,
        "session_id": session_id,
        "fixed": fixed,
        "attempted_action": attempted_action,
        "confirmed_cause": confirmed_cause,
    }

    result = client.table("case_feedback").insert(data).execute()

    outcome = (
        f"Resolved using: {attempted_action}"
        if fixed
        else f"Not resolved after: {attempted_action}"
    )

    client.table("case_history").update(
        {"outcome": outcome}
    ).eq("id", case_id).execute()

    return result.data[0] if result.data else data