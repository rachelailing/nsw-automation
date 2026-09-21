"""Knowledge Pack lookup helpers."""

import os

from db.supabase_client import get_client


DEFAULT_PROJECT_NAME = os.getenv(
    "DEFAULT_PROJECT_NAME",
    "Demo Dispensing Project",
)


async def get_active_knowledge_pack(project_id: int | None = None) -> dict:
    """Return the approved Knowledge Pack used for a new session."""
    client = get_client()

    if project_id is None:
        project_result = (
            client.table("projects")
            .select("id, name")
            .eq("name", DEFAULT_PROJECT_NAME)
            .limit(1)
            .execute()
        )
        if not project_result.data:
            raise RuntimeError(
                f"Default project '{DEFAULT_PROJECT_NAME}' does not exist. "
                "Run database/schema.sql in Supabase."
            )
        project_id = project_result.data[0]["id"]

    pack_result = (
        client.table("knowledge_packs")
        .select("id, project_id, name, version, status, approved_at")
        .eq("project_id", project_id)
        .eq("status", "approved")
        .order("approved_at", desc=True)
        .limit(1)
        .execute()
    )
    if not pack_result.data:
        raise RuntimeError(
            f"Project {project_id} has no approved Knowledge Pack."
        )

    return pack_result.data[0]
