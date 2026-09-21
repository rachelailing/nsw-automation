"""Retrieve completed reports and generate downloadable PDFs."""

import re

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from db.sessions import get_session
from report.pdf_generator import generate_pdf


router = APIRouter()


class ReportResponse(BaseModel):
    session_id: str
    report: dict
    defect_type: str
    pdf_url: str


async def _completed_session(session_id: str) -> tuple[dict, dict]:
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    state = session.get("state") or {}
    if not state.get("report"):
        raise HTTPException(
            status_code=409,
            detail="The troubleshooting analysis is not complete yet.",
        )
    return session, state


@router.get("/report/{session_id}", response_model=ReportResponse)
async def get_report(session_id: str):
    _, state = await _completed_session(session_id)
    return ReportResponse(
        session_id=session_id,
        report=state["report"],
        defect_type=state.get("defect_type") or "Unknown defect",
        pdf_url=f"/api/report/{session_id}/pdf",
    )


@router.get("/report/{session_id}/pdf")
async def download_report_pdf(session_id: str):
    session, state = await _completed_session(session_id)
    pdf_bytes = await generate_pdf({**session, "state": state})
    defect_slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        (state.get("defect_type") or "troubleshooting").lower(),
    ).strip("-")
    filename = f"{defect_slug or 'troubleshooting'}-{session_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
