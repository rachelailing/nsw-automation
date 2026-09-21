import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from ai.orchestrator import run_orchestrator


class TestOrchestrator(unittest.IsolatedAsyncioTestCase):

    async def test_questioning_starts_with_material_question(self):
        session_state = {"step": "questioning", "qa_pairs": [], "pending_questions": []}

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Hi",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "questioning")
        self.assertIn("what kind of material", result["reply"])
        self.assertEqual(result["updated_state"]["problem_description"], "Hi")
        self.assertEqual(result["updated_state"]["diagnostic_stage"], "material")

    async def test_material_answer_moves_to_diameter_question(self):
        session_state = {
            "step": "questioning",
            "problem_description": "Hi",
            "qa_pairs": [],
            "pending_questions": [],
            "diagnostic_stage": "material",
            "workflow_started": True,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Solder paste",
            session_state=session_state,
        )

        self.assertIn("Got it, Solder paste", result["reply"])
        self.assertIn("exact measured diameter", result["reply"])
        self.assertEqual(result["updated_state"]["diagnostic_stage"], "diameter")

    @patch("ai.orchestrator.build_reference_threshold_context", new_callable=AsyncMock)
    async def test_diameter_answer_cites_threshold_before_next_question(
        self,
        mock_threshold_context,
    ):
        evaluation = {
            "threshold_row": {"material": "solder paste"},
            "checks": [
                {
                    "parameter": "diameter",
                    "measured": 0.95,
                    "min": 0.40,
                    "target": 0.50,
                    "max": 0.60,
                    "status": "above_max",
                    "interpretation": "Measured value is above the acceptable maximum.",
                }
            ],
        }
        mock_threshold_context.return_value = ("Reference Threshold Checks", evaluation)
        session_state = {
            "step": "questioning",
            "problem_description": "Hi",
            "qa_pairs": [
                {"question": "What material?", "answer": "Solder paste"},
            ],
            "pending_questions": [],
            "diagnostic_stage": "diameter",
            "workflow_started": True,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="It is too large, around 0.95 mm.",
            session_state=session_state,
        )

        self.assertIn("0.95 mm is above the 0.60 mm maximum", result["reply"])
        self.assertIn("continuously on every part", result["reply"])
        self.assertEqual(
            result["updated_state"]["diagnostic_stage"],
            "frequency_and_changes",
        )

    @patch("ai.orchestrator.generate_report_and_save_case", new_callable=AsyncMock)
    @patch("ai.orchestrator.rank_causes", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_text_defect_agent", new_callable=AsyncMock)
    async def test_questioning_calls_text_defect_agent_when_enough_info(
        self,
        mock_text_defect_agent,
        mock_rank_causes,
        mock_generate_report,
    ):
        mock_text_defect_agent.return_value = {
            "defect_type": "Undersized Dot",
            "confidence": 0.88,
            "reasoning": "The answers point to too little material being dispensed.",
        }

        async def rank_causes_side_effect(state, qa_pairs):
            state["causes"] = [
                {
                    "rank": 1,
                    "cause": "Dispensing pressure is too low",
                    "category": "Dispensing Parameters",
                    "confidence": 0.8,
                    "reasoning": "The dots are continuously undersized.",
                }
            ]
            return {"causes": state["causes"], "rag_context_used": False}

        async def generate_report_side_effect(session_id, state, qa_pairs):
            state["report"] = {
                "summary": "Undersized dots were identified.",
                "action_plan": [
                    {
                        "step_number": 1,
                        "action": "Restore and verify dispensing pressure.",
                        "rationale": "Pressure is the top suspected cause.",
                        "priority": "high",
                    }
                ],
                "recommendations": [],
            }
            state["step"] = "done"
            state["case_history_saved"] = True
            state["case_history_id"] = 123
            return state["report"]

        mock_rank_causes.side_effect = rank_causes_side_effect
        mock_generate_report.side_effect = generate_report_side_effect

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
            "diagnostic_stage": "location",
            "workflow_started": True,
            "reference_threshold_evaluation": {"checks": []},
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="It happens continuously.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "done")
        self.assertIn("Undersized Dot", result["reply"])
        self.assertIn("Dispensing pressure is too low", result["reply"])
        self.assertIn("Did this fix the issue?", result["reply"])
        self.assertEqual(result["updated_state"]["defect_type"], "Undersized Dot")
        self.assertEqual(result["updated_state"]["step"], "done")
        mock_text_defect_agent.assert_awaited_once()
        text_agent_call = mock_text_defect_agent.call_args.kwargs
        self.assertEqual(text_agent_call["problem_description"], "The dots are too small.")
        self.assertEqual(text_agent_call["qa_pairs"][-1]["answer"], "It happens continuously.")
        mock_rank_causes.assert_awaited_once()
        mock_generate_report.assert_awaited_once_with(
            "session-1",
            result["updated_state"],
            result["updated_state"]["qa_pairs"],
        )

    @patch("ai.orchestrator.generate_report_and_save_case", new_callable=AsyncMock)
    @patch("ai.orchestrator.rank_causes", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_image_defect_agent", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_text_defect_agent", new_callable=AsyncMock)
    async def test_questioning_calls_text_and_image_defect_agents_when_image_exists(
        self,
        mock_text_defect_agent,
        mock_image_defect_agent,
        mock_rank_causes,
        mock_generate_report,
    ):
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

        async def rank_causes_side_effect(state, qa_pairs):
            state["causes"] = [
                {
                    "rank": 1,
                    "cause": "The replacement nozzle is misaligned",
                    "category": "Nozzle Condition",
                    "confidence": 0.8,
                    "reasoning": "The shape changed after the nozzle replacement.",
                }
            ]
            return {"causes": state["causes"], "rag_context_used": False}

        async def generate_report_side_effect(session_id, state, qa_pairs):
            state["report"] = {
                "summary": "An irregular dot shape was identified.",
                "action_plan": [
                    {
                        "step_number": 1,
                        "action": "Inspect and realign the nozzle.",
                        "rationale": "The nozzle was recently changed.",
                        "priority": "high",
                    }
                ],
                "recommendations": [],
            }
            state["step"] = "done"
            return state["report"]

        mock_rank_causes.side_effect = rank_causes_side_effect
        mock_generate_report.side_effect = generate_report_side_effect

        session_state = {
            "step": "questioning",
            "problem_description": "The glue dot has a tail.",
            "qa_pairs": [],
            "pending_questions": [],
            "image_url": "https://example.com/defect.png",
            "diagnostic_stage": "location",
            "workflow_started": True,
            "reference_threshold_evaluation": {"checks": []},
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Nozzle was recently changed.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "done")
        self.assertIn("Irregular Shape", result["reply"])
        self.assertIn("The replacement nozzle is misaligned", result["reply"])
        self.assertEqual(result["updated_state"]["defect_result"]["source"], "text_and_image")
        mock_text_defect_agent.assert_awaited_once()
        mock_image_defect_agent.assert_awaited_once_with(
            image_url="https://example.com/defect.png",
            image_bytes=None,
        )

    @patch("ai.orchestrator.run_image_defect_agent", new_callable=AsyncMock)
    async def test_photo_first_analyzes_image_before_asking_remaining_questions(
        self,
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
        self.assertIn("what kind of material", result["reply"])
        self.assertEqual(
            result["updated_state"]["image_result"]["defect_type"],
            "Excessive Spreading",
        )


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

    @patch("ai.orchestrator.save_completed_case", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_report_agent", new_callable=AsyncMock)
    async def test_reporting_step_calls_report_agent_and_marks_done(
        self,
        mock_report_agent,
        mock_save_completed_case,
    ):
        mock_save_completed_case.return_value = {"id": 123}
        mock_report_agent.return_value = {
            "summary": "Undersized Dot was identified; low pressure is the top suspected cause.",
            "action_plan": [
                {
                    "step_number": 1,
                    "action": "Check dispensing pressure.",
                    "rationale": "Low pressure is ranked as the most likely cause.",
                    "priority": "high",
                }
            ],
            "recommendations": ["Log validated pressure settings after setup."],
        }

        session_state = {
            "step": "reporting",
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
            "causes": [
                {
                    "rank": 1,
                    "cause": "Dispensing pressure is too low",
                    "category": "Dispensing Parameters",
                    "confidence": 0.6,
                    "reasoning": "The defect is continuous and dots are undersized.",
                }
            ],
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Generate report",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "done")
        self.assertEqual(result["updated_state"]["step"], "done")
        self.assertIn("Troubleshooting report generated", result["reply"])
        self.assertIn("Check dispensing pressure", result["reply"])
        self.assertEqual(
            result["updated_state"]["report"]["summary"],
            "Undersized Dot was identified; low pressure is the top suspected cause.",
        )
        self.assertTrue(result["updated_state"]["case_history_saved"])
        self.assertEqual(result["updated_state"]["case_history_id"], 123)

        call_args = mock_report_agent.call_args
        self.assertEqual(call_args.kwargs["defect_type"], "Undersized Dot")
        self.assertEqual(call_args.kwargs["causes"], session_state["causes"])
        self.assertIn("Defect identification", call_args.kwargs["problem_description"])
        self.assertEqual(call_args.kwargs["qa_pairs"], session_state["qa_pairs"])

        save_call_args = mock_save_completed_case.call_args
        self.assertEqual(save_call_args.kwargs["session_id"], "session-1")
        self.assertEqual(save_call_args.kwargs["defect_type"], "Undersized Dot")
        self.assertEqual(save_call_args.kwargs["causes"], session_state["causes"])
        self.assertIn("The dots are too small.", save_call_args.kwargs["problem_description"])
        self.assertIn("Troubleshooting report generated", save_call_args.kwargs["action_plan"])

    @patch("ai.orchestrator.save_completed_case", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_report_agent", new_callable=AsyncMock)
    async def test_reporting_step_does_not_duplicate_saved_case(
        self,
        mock_report_agent,
        mock_save_completed_case,
    ):
        mock_report_agent.return_value = {
            "summary": "Report already generated.",
            "action_plan": [
                {
                    "step_number": 1,
                    "action": "Check dispensing pressure.",
                    "rationale": "Low pressure is ranked as the most likely cause.",
                    "priority": "high",
                }
            ],
            "recommendations": [],
        }

        session_state = {
            "step": "reporting",
            "problem_description": "The dots are too small.",
            "qa_pairs": [],
            "defect_type": "Undersized Dot",
            "causes": [
                {
                    "rank": 1,
                    "cause": "Dispensing pressure is too low",
                    "category": "Dispensing Parameters",
                    "confidence": 0.6,
                    "reasoning": "The defect is continuous and dots are undersized.",
                }
            ],
            "case_history_saved": True,
            "case_history_id": 123,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Generate report again",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "done")
        self.assertEqual(result["updated_state"]["case_history_id"], 123)
        mock_save_completed_case.assert_not_awaited()

    async def test_reporting_step_without_required_data_returns_to_ranking(self):
        session_state = {
            "step": "reporting",
            "problem_description": "The dots are too small.",
            "qa_pairs": [],
            "defect_type": "Undersized Dot",
            "causes": [],
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Generate report",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "ranking")
        self.assertIn("ranked causes", result["reply"])


if __name__ == "__main__":
    unittest.main()
