"""
Sessions — Supabase queries for managing conversation sessions.

Each user's in-progress conversation (questions asked, answers given,
current step) is stored in Supabase so multiple users can use the tool
simultaneously without sessions mixing up.
"""

import uuid
from db.supabase_client import get_client
from db.knowledge_packs import get_active_knowledge_pack


def default_session_state(
    project_id: int | None = None,
    knowledge_pack_id: int | None = None,
) -> dict:
    """Return the initial state expected by the orchestrator."""
    return {
        "step": "questioning",
        "problem_description": "",
        "qa_pairs": [],
        "pending_questions": [],
        "diagnostic_stage": "material",
        "workflow_started": False,
        "project_id": project_id,
        "knowledge_pack_id": knowledge_pack_id,
    }


async def create_session() -> dict:
    """
    Create a new troubleshooting session.

    Returns:
        dict with session_id and initial state
    """
    client = get_client()
    session_id = str(uuid.uuid4())
    active_pack = await get_active_knowledge_pack()
    initial_state = default_session_state(
        project_id=active_pack["project_id"],
        knowledge_pack_id=active_pack["id"],
    )
    data = {
        "session_id": session_id,
        "project_id": active_pack["project_id"],
        "knowledge_pack_id": active_pack["id"],
        "step": "questioning",
        "conversation_history": [],
        "problem_description": "",
        "qa_pairs": [],
        "state": initial_state,
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


async def get_or_create_session_state(session_id: str) -> dict:
    """
    Retrieve the persisted orchestrator state for a session.

    If the session does not exist yet, create it with the default state.
    """
    client = get_client()
    result = (
        client.table("sessions")
        .select("*")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )

    if result.data:
        row = result.data[0]
        state = row.get("state") or {}
        if state:
            project_id = state.get("project_id") or row.get("project_id")
            knowledge_pack_id = (
                state.get("knowledge_pack_id") or row.get("knowledge_pack_id")
            )
            if not project_id or not knowledge_pack_id:
                active_pack = await get_active_knowledge_pack(project_id=project_id)
                project_id = active_pack["project_id"]
                knowledge_pack_id = active_pack["id"]
            state["project_id"] = project_id
            state["knowledge_pack_id"] = knowledge_pack_id
            return state

        project_id = row.get("project_id")
        knowledge_pack_id = row.get("knowledge_pack_id")
        if not project_id or not knowledge_pack_id:
            active_pack = await get_active_knowledge_pack(project_id=project_id)
            project_id = active_pack["project_id"]
            knowledge_pack_id = active_pack["id"]

        return {
            "step": row.get("step") or "questioning",
            "problem_description": row.get("problem_description") or "",
            "qa_pairs": row.get("qa_pairs") or [],
            "pending_questions": [],
            "defect_type": row.get("defect_type"),
            "causes": row.get("causes") or [],
            "image_url": row.get("image_url"),
            "project_id": project_id,
            "knowledge_pack_id": knowledge_pack_id,
        }

    active_pack = await get_active_knowledge_pack()
    initial_state = default_session_state(
        project_id=active_pack["project_id"],
        knowledge_pack_id=active_pack["id"],
    )
    client.table("sessions").insert(
        {
            "session_id": session_id,
            "project_id": active_pack["project_id"],
            "knowledge_pack_id": active_pack["id"],
            "step": initial_state["step"],
            "problem_description": initial_state["problem_description"],
            "conversation_history": [],
            "qa_pairs": initial_state["qa_pairs"],
            "state": initial_state,
            "defect_type": None,
            "causes": None,
            "image_url": None,
        }
    ).execute()
    return initial_state


async def save_session_state(
    session_id: str,
    state: dict,
    user_message: str | None = None,
    assistant_reply: str | None = None,
) -> dict:
    """
    Persist the full orchestrator state and mirror key fields for queries.
    """
    client = get_client()

    result = (
        client.table("sessions")
        .select("conversation_history")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    history = result.data[0].get("conversation_history") if result.data else []
    history = history or []

    if user_message:
        history.append({"role": "user", "content": user_message})
    if assistant_reply:
        history.append({"role": "assistant", "content": assistant_reply})

    updates = {
        "step": state.get("step", "questioning"),
        "problem_description": state.get("problem_description", ""),
        "conversation_history": history,
        "qa_pairs": state.get("qa_pairs", []),
        "state": state,
        "defect_type": state.get("defect_type"),
        "causes": state.get("causes"),
        "image_url": state.get("image_url"),
        "project_id": state.get("project_id"),
        "knowledge_pack_id": state.get("knowledge_pack_id"),
    }

    update_result = (
        client.table("sessions")
        .update(updates)
        .eq("session_id", session_id)
        .execute()
    )
    return update_result.data[0] if update_result.data else updates
