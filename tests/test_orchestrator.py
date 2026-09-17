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

    @patch("ai.orchestrator.run_image_defect_agent", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_text_defect_agent", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_question_agent", new_callable=AsyncMock)
    async def test_questioning_calls_text_and_image_defect_agents_when_image_exists(
        self,
        mock_question_agent,
        mock_text_defect_agent,
        mock_image_defect_agent,
    ):
        mock_question_agent.return_value = {
            "questions": [],
            "enough_info": True,
        }
        mock_text_defect_agent.return_value = {
            "defect_type": "Irregular Shape",
            "confidence": 0.7,
            "reasoning": "The description mentions tails and uneven dot shape.",
        }
        mock_image_defect_agent.return_value = {
            "defect_type": "Irregular Shape",
            "confidence": 0.9,
            "reasoning": "The uploaded image shows asymmetry and satellite droplets.",
            "observations": ["asymmetric dot", "satellite droplets"],
        }

        session_state = {
            "step": "questioning",
            "problem_description": "The glue dot has a tail.",
            "qa_pairs": [],
            "pending_questions": [],
            "image_url": "https://example.com/defect.png",
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Nozzle was recently changed.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "ranking")
        self.assertIn("Irregular Shape", result["reply"])
        self.assertIn("text_and_image", result["reply"])
        self.assertEqual(result["updated_state"]["defect_result"]["source"], "text_and_image")
        mock_text_defect_agent.assert_awaited_once()
        mock_image_defect_agent.assert_awaited_once_with(
            image_url="https://example.com/defect.png",
            image_bytes=None,
        )

    @patch("ai.orchestrator.run_image_defect_agent", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_question_agent", new_callable=AsyncMock)
    async def test_photo_first_analyzes_image_before_asking_remaining_questions(
        self,
        mock_question_agent,
        mock_image_defect_agent,
    ):
        mock_image_defect_agent.return_value = {
            "defect_type": "Excessive Spreading",
            "confidence": 0.84,
            "reasoning": "The dot boundary appears wide and wet.",
            "observations": ["wide wetting area"],
            "likely_visible_symptoms": ["material spreading beyond dot boundary"],
            "unanswered_context_needed": ["material type", "defect frequency"],
            "image_quality_notes": "Image is clear enough for preliminary classification.",
        }
        mock_question_agent.return_value = {
            "questions": ["What material is being dispensed?"],
            "enough_info": False,
        }

        session_state = {
            "step": "questioning",
            "problem_description": "",
            "qa_pairs": [],
            "pending_questions": [],
            "image_url": "https://example.com/defect.png",
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Image uploaded",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "questioning")
        self.assertEqual(result["reply"], "What material is being dispensed?")
        self.assertEqual(
            result["updated_state"]["image_result"]["defect_type"],
            "Excessive Spreading",
        )

        call_args = mock_question_agent.call_args
        question_context = call_args.kwargs["problem_description"]
        self.assertIn("Uploaded Image Analysis", question_context)
        self.assertIn("Excessive Spreading", question_context)
        self.assertIn("Ask only for information", question_context)

    @patch("ai.orchestrator.run_cause_ranking_agent", new_callable=AsyncMock)
    @patch("ai.orchestrator.get_similar_cases", new_callable=AsyncMock)
    async def test_ranking_step_calls_cause_ranking_agent_with_similar_cases(
        self,
        mock_get_similar_cases,
        mock_cause_ranking_agent,
    ):
        mock_get_similar_cases.return_value = [
            {
                "problem_description": "Small dots on previous run",
                "defect_type": "Undersized Dot",
                "causes": [{"cause": "Low pressure"}],
                "action_plan": "Increase pressure.",
                "outcome": "Fixed",
            }
        ]
        mock_cause_ranking_agent.return_value = {
            "causes": [
                {
                    "rank": 1,
                    "cause": "Dispensing pressure is too low",
                    "category": "Dispensing Parameters",
                    "confidence": 0.6,
                    "reasoning": "The defect is continuous and dots are undersized.",
                }
            ],
            "rag_context_used": True,
        }

        session_state = {
            "step": "ranking",
            "problem_description": "The dots are too small.",
            "qa_pairs": [
                {"question": "Is it continuous?", "answer": "Yes, every cycle."}
            ],
            "defect_type": "Undersized Dot",
            "defect_result": {
                "defect_type": "Undersized Dot",
                "confidence": 0.88,
                "source": "text",
                "reasoning": "The answers point to insufficient material.",
            },
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Rank causes",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "reporting")
        self.assertIn("Dispensing pressure is too low", result["reply"])
        self.assertEqual(result["updated_state"]["step"], "reporting")
        self.assertEqual(len(result["updated_state"]["causes"]), 1)
        mock_get_similar_cases.assert_awaited_once_with("Undersized Dot")

        call_args = mock_cause_ranking_agent.call_args
        self.assertEqual(call_args.kwargs["defect_type"], "Undersized Dot")
        self.assertIn("Defect identification summary", call_args.kwargs["problem_description"])
        self.assertEqual(call_args.kwargs["similar_cases"], mock_get_similar_cases.return_value)

    async def test_ranking_step_without_defect_type_returns_to_questioning(self):
        session_state = {
            "step": "ranking",
            "problem_description": "The dots are too small.",
            "qa_pairs": [],
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Rank causes",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "questioning")
        self.assertIn("identify the defect type", result["reply"])


if __name__ == "__main__":
    unittest.main()
