"""
Report API — Generate and retrieve troubleshooting reports.

Returns the final structured report for a completed session,
and optionally generates a PDF (Bonus 4).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ReportResponse(BaseModel):
    session_id: str
    report_text: str
    pdf_url: str | None = None


@router.get("/report/{session_id}", response_model=ReportResponse)
async def get_report(session_id: str):
    """
    Retrieve or generate the final report for a session.

    TODO:
    - Load completed case from Supabase
    - Format into structured report
    - Optionally generate PDF via report/pdf_generator.py
    - Return report text and optional PDF download URL
    """
    return ReportResponse(
        session_id=session_id,
        report_text="[Placeholder] Report not yet generated.",
        pdf_url=None,
    )
