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
SESSION_STATES: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    step: str  # e.g. "questioning", "identifying", "ranking", "reporting", "done"


from ai.orchestrator import run_orchestrator
import traceback

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a user message and get the orchestrator's response.
    """
    try:
        session_state = SESSION_STATES.setdefault(
            request.session_id,
            {
                "step": "questioning",
                "problem_description": "",
                "qa_pairs": [],
                "pending_questions": [],
            },
        )
        
        result = await run_orchestrator(
            session_id=request.session_id,
            user_message=request.message,
            session_state=session_state
        )

        SESSION_STATES[request.session_id] = result["updated_state"]
        
        return ChatResponse(
            session_id=request.session_id,
            reply=result["reply"],
            step=result["step"],
        )
    except Exception as e:
        print(f"Error calling orchestrator: {traceback.format_exc()}")
        return ChatResponse(
            session_id=request.session_id,
            reply=f"Backend Error: {str(e)}",
            step="error",
        )
