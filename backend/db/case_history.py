"""
Case History — Supabase queries for the learning database (RAG).

Stores completed troubleshooting cases and retrieves similar past cases
to provide context for the Cause Ranking Agent.
"""

from db.supabase_client import get_client


async def save_case(
    session_id: str,
    problem_description: str,
    defect_type: str,
    causes: list[dict],
    action_plan: str,
    outcome: str | None = None,
    project_id: int | None = None,
    knowledge_pack_id: int | None = None,
) -> dict:
    """
    Save a completed troubleshooting case to the case_history table.

    This is called at the end of each session to grow the RAG database.

    TODO:
    - Insert row into case_history table
    - Return the inserted row
    """
    client = get_client()
    data = {
        "session_id": session_id,
        "problem_description": problem_description,
        "defect_type": defect_type,
        "causes": causes,
        "action_plan": action_plan,
        "outcome": outcome,
        "project_id": project_id,
        "knowledge_pack_id": knowledge_pack_id,
    }
    result = client.table("case_history").insert(data).execute()
    return result.data[0] if result.data else {}


async def get_similar_cases(
    defect_type: str,
    project_id: int | None = None,
    knowledge_pack_id: int | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve similar past cases for RAG context.

    Uses keyword/tag matching (Option A from implementation.md):
    Query cases with the same defect_type, ordered by most recent.

    Args:
        defect_type: The identified defect type to match against
        limit: Maximum number of past cases to return

    Returns:
        List of case dicts with keys: problem_description, causes, action_plan, outcome

    TODO:
    - Query case_history WHERE defect_type matches
    - Order by created_at DESC
    - Return top N results
    """
    client = get_client()
    query = (
        client.table("case_history")
        .select("problem_description, defect_type, causes, action_plan, outcome, created_at")
        .eq("defect_type", defect_type)
    )
    if project_id is not None:
        query = query.eq("project_id", project_id)
    if knowledge_pack_id is not None:
        query = query.eq("knowledge_pack_id", knowledge_pack_id)

    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data if result.data else []
