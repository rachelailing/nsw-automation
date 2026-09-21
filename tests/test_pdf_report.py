import io
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from pypdf import PdfReader

os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from api.report import download_report_pdf, get_report
from report.pdf_generator import generate_pdf


SAMPLE_STATE = {
    "step": "awaiting_feedback",
    "project_id": 10,
    "knowledge_pack_id": 20,
    "defect_type": "Oversized Dot",
    "defect_result": {
        "defect_type": "Oversized Dot",
        "confidence": 0.95,
        "source": "text",
        "reasoning": "The measured dot exceeds the approved maximum.",
    },
    "qa_pairs": [
        {"question": "What material is being dispensed?", "answer": "Solder paste"},
        {"question": "Is the defect continuous?", "answer": "Yes, every part"},
    ],
    "reference_threshold_evaluation": {
        "checks": [
            {
                "parameter": "diameter",
                "measured": 0.95,
                "min": 0.4,
                "max": 0.6,
                "unit": "mm",
                "status": "above_max",
            }
        ]
    },
    "causes": [
        {
            "rank": 1,
            "cause": "Dispensing pressure or time is too high",
            "category": "Dispensing Parameters",
            "confidence": 0.75,
            "reasoning": "Continuous oversized dots indicate excess volume.",
        }
    ],
    "report": {
        "summary": "An oversized solder paste dot was confirmed.",
        "action_plan": [
            {
                "step_number": 1,
                "action": "Verify pressure against the approved recipe.",
                "rationale": "Excess pressure increases delivered volume.",
                "priority": "high",
            }
        ],
        "recommendations": ["Record the validated pressure after setup."],
    },
}


class TestPdfReport(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_contains_diagnosis_and_actions(self):
        pdf_bytes = await generate_pdf(
            {
                "session_id": "11111111-2222-3333-4444-555555555555",
                "project_id": 10,
                "knowledge_pack_id": 20,
                "state": SAMPLE_STATE,
            }
        )

        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("Troubleshooting Report", text)
        self.assertIn("Oversized Dot", text)
        self.assertIn("0.95 mm", text)
        self.assertIn("Verify pressure against the approved recipe", text)

    @patch("api.report.get_session", new_callable=AsyncMock)
    async def test_report_requires_completed_analysis(self, mock_get_session):
        mock_get_session.return_value = {
            "session_id": "session-1",
            "state": {"step": "questioning"},
        }

        with self.assertRaises(HTTPException) as raised:
            await get_report("session-1")

        self.assertEqual(raised.exception.status_code, 409)

    @patch("api.report.get_session", new_callable=AsyncMock)
    async def test_download_response_is_pdf_attachment(self, mock_get_session):
        mock_get_session.return_value = {
            "session_id": "11111111-2222-3333-4444-555555555555",
            "project_id": 10,
            "knowledge_pack_id": 20,
            "state": SAMPLE_STATE,
        }

        response = await download_report_pdf("11111111-2222-3333-4444-555555555555")

        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn("oversized-dot-11111111.pdf", response.headers["content-disposition"])
        self.assertTrue(response.body.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
