"""
Chat API — Main conversation endpoint.

Handles the ongoing troubleshooting conversation between the user and the
Main Orchestrator. Each request includes the session_id and the user's
latest message; the orchestrator decides what to do next (ask follow-up
questions, call a subagent, etc.) and returns the AI's reply.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    step: str  # e.g. "questioning", "identifying", "ranking", "reporting", "done"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a user message and get the orchestrator's response.

    TODO:
    - Load session state from Supabase
    - Pass to orchestrator.run()
    - Save updated session state
    - Return AI reply
    """
    # Placeholder — replace with orchestrator call
    return ChatResponse(
        session_id=request.session_id,
        reply="[Placeholder] Orchestrator not yet implemented.",
        step="questioning",
    )
