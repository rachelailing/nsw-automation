import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from ai.orchestrator import run_orchestrator


class TestOrchestrator(unittest.IsolatedAsyncioTestCase):

    @patch("ai.orchestrator.run_question_agent", new_callable=AsyncMock)
    async def test_questioning_stores_initial_problem_and_pending_questions(self, mock_question_agent):
        mock_question_agent.return_value = {
            "questions": [
                "Is the dispensing amount too large or too small?",
                "Is the defect continuous or occasional?",
            ],
            "enough_info": False,
        }

        session_state = {"step": "questioning", "qa_pairs": [], "pending_questions": []}

        result = await run_orchestrator(
            session_id="session-1",
            user_message="The dots are too small.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "questioning")
        self.assertEqual(result["reply"], "Is the dispensing amount too large or too small?")
        self.assertEqual(result["updated_state"]["problem_description"], "The dots are too small.")
        self.assertEqual(
            result["updated_state"]["pending_questions"],
            [
                "Is the dispensing amount too large or too small?",
                "Is the defect continuous or occasional?",
            ],
        )

    @patch("ai.orchestrator.run_text_defect_agent", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_question_agent", new_callable=AsyncMock)
    async def test_questioning_calls_text_defect_agent_when_enough_info(
        self,
        mock_question_agent,
        mock_text_defect_agent,
    ):
        mock_question_agent.return_value = {
            "questions": [],
            "enough_info": True,
        }
        mock_text_defect_agent.return_value = {
            "defect_type": "Undersized Dot",
            "confidence": 0.88,
            "reasoning": "The answers point to too little material being dispensed.",
        }

        session_state = {
            "step": "questioning",
            "problem_description": "The dots are too small.",
            "qa_pairs": [
                {
                    "question": "Is the dispensing amount too large or too small?",
                    "answer": "Too small.",
                }
            ],
            "pending_questions": [],
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="It happens continuously.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "ranking")
        self.assertIn("Undersized Dot", result["reply"])
        self.assertEqual(result["updated_state"]["defect_type"], "Undersized Dot")
        mock_text_defect_agent.assert_awaited_once_with(
            problem_description="The dots are too small.",
            qa_pairs=[
                {
                    "question": "Is the dispensing amount too large or too small?",
                    "answer": "Too small.",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
