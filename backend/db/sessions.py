"""
Sessions — Supabase queries for managing conversation sessions.

Each user's in-progress conversation (questions asked, answers given,
current step) is stored in Supabase so multiple users can use the tool
simultaneously without sessions mixing up.
"""

import uuid
from db.supabase_client import get_client


async def create_session() -> dict:
    """
    Create a new troubleshooting session.

    Returns:
        dict with session_id and initial state
    """
    client = get_client()
    session_id = str(uuid.uuid4())
    data = {
        "session_id": session_id,
        "step": "questioning",
        "conversation_history": [],
        "problem_description": "",
        "qa_pairs": [],
        "defect_type": None,
        "causes": None,
        "image_url": None,
    }
    result = client.table("sessions").insert(data).execute()
    return result.data[0] if result.data else data


async def get_session(session_id: str) -> dict | None:
    """Retrieve a session by ID."""
    client = get_client()
    result = (
        client.table("sessions")
        .select("*")
        .eq("session_id", session_id)
        .single()
        .execute()
    )
    return result.data


async def update_session(session_id: str, updates: dict) -> dict:
    """
    Update a session with new data.

    Args:
        session_id: The session to update
        updates: Dict of fields to update (e.g., step, qa_pairs, defect_type)

    Returns:
        The updated session data
    """
    client = get_client()
    result = (
        client.table("sessions")
        .update(updates)
        .eq("session_id", session_id)
        .execute()
    )
    return result.data[0] if result.data else {}
