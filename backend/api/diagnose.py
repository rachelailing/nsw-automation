"""
Diagnose API — Trigger a full diagnosis run.

This endpoint can be called when enough information has been gathered
and the user (or orchestrator) wants to run the full pipeline:
Text/Image Defect ID → Cause Ranking → Report.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DiagnoseRequest(BaseModel):
    session_id: str


class DiagnoseResponse(BaseModel):
    session_id: str
    defect_type: str
    causes: list  # ranked list of {cause, confidence, reasoning}
    action_plan: str


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest):
    """
    Run the full diagnosis pipeline for a session.

    TODO:
    - Load session data (answers + optional image) from Supabase
    - Call Text Defect ID Agent (and Image Defect ID Agent in parallel if image exists)
    - Call Cause Ranking Agent with RAG context
    - Call Report Agent
    - Save completed case to case_history
    - Return results
    """
    return DiagnoseResponse(
        session_id=request.session_id,
        defect_type="[Placeholder]",
        causes=[],
        action_plan="[Placeholder] Not yet implemented.",
    )
