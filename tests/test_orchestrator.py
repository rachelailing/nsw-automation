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
            "project_id": 10,
            "knowledge_pack_id": 20,
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
            "frequency",
        )
        mock_threshold_context.assert_awaited_once_with(
            problem_description="Hi",
            qa_pairs=result["updated_state"]["qa_pairs"],
            project_id=10,
            knowledge_pack_id=20,
        )

    async def test_repeated_answer_is_not_accepted_for_next_stage(self):
        repeated_answer = "It is too large, around 0.95 mm."
        session_state = {
            "step": "questioning",
            "problem_description": "Hi",
            "qa_pairs": [
                {"question": "What material?", "answer": "Solder paste"},
                {"question": "What diameter?", "answer": repeated_answer},
            ],
            "pending_questions": [],
            "diagnostic_stage": "frequency",
            "workflow_started": True,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message=repeated_answer,
            session_state=session_state,
        )

        self.assertEqual(result["step"], "questioning")
        self.assertIn("repeat your previous answer", result["reply"])
        self.assertIn("continuously on every part", result["reply"])
        self.assertEqual(
            result["updated_state"]["diagnostic_stage"],
            "frequency",
        )
        self.assertEqual(len(result["updated_state"]["qa_pairs"]), 2)

    async def test_irrelevant_frequency_answer_requests_clarification(self):
        session_state = {
            "step": "questioning",
            "problem_description": "Hi",
            "qa_pairs": [],
            "pending_questions": [],
            "diagnostic_stage": "frequency",
            "workflow_started": True,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="The dot is 0.95 mm.",
            session_state=session_state,
        )

        self.assertIn("could not tell how often", result["reply"])
        self.assertEqual(
            result["updated_state"]["diagnostic_stage"],
            "frequency",
        )
        self.assertEqual(result["updated_state"]["qa_pairs"], [])

    async def test_future_location_answer_is_saved_while_frequency_is_reasked(self):
        session_state = {
            "step": "questioning",
            "problem_description": "The solder paste dot is oversized.",
            "qa_pairs": [],
            "pending_questions": [],
            "diagnostic_stage": "frequency",
            "workflow_started": True,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="It is happening across multiple locations on the board.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "questioning")
        self.assertIn("noted that detail for the location step", result["reply"])
        self.assertIn("how often", result["reply"])
        self.assertEqual(result["updated_state"]["diagnostic_stage"], "frequency")
        self.assertEqual(result["updated_state"]["qa_pairs"], [])
        self.assertEqual(
            result["updated_state"]["deferred_diagnostic_answers"]["location"],
            "It is happening across multiple locations on the board.",
        )

    @patch("ai.orchestrator.generate_report_and_save_case", new_callable=AsyncMock)
    @patch("ai.orchestrator.rank_causes", new_callable=AsyncMock)
    @patch("ai.orchestrator.run_text_defect_agent", new_callable=AsyncMock)
    async def test_saved_location_answer_is_not_asked_again(
        self,
        mock_text_defect_agent,
        mock_rank_causes,
        mock_generate_report,
    ):
        mock_text_defect_agent.return_value = {
            "defect_type": "Oversized Dot",
            "confidence": 0.95,
            "reasoning": "The measured dot exceeds the maximum diameter.",
        }

        async def rank_causes_side_effect(state, qa_pairs):
            state["causes"] = [{
                "rank": 1,
                "cause": "Dispensing pressure is too high",
                "confidence": 0.85,
                "reasoning": "The defect is continuous across multiple locations.",
            }]
            return {"causes": state["causes"]}

        async def generate_report_side_effect(session_id, state, qa_pairs):
            state["report"] = {
                "summary": "An oversized dot was identified.",
                "action_plan": [{
                    "step_number": 1,
                    "action": "Verify the dispensing pressure.",
                }],
            }
            state["step"] = "awaiting_feedback"
            return state["report"]

        mock_rank_causes.side_effect = rank_causes_side_effect
        mock_generate_report.side_effect = generate_report_side_effect

        session_state = {
            "step": "questioning",
            "problem_description": "The solder paste dot is oversized.",
            "qa_pairs": [],
            "pending_questions": [],
            "diagnostic_stage": "frequency",
            "workflow_started": True,
            "reference_threshold_evaluation": {"checks": []},
        }

        location_result = await run_orchestrator(
            session_id="session-1",
            user_message="It is happening across multiple locations on the board.",
            session_state=session_state,
        )
        frequency_result = await run_orchestrator(
            session_id="session-1",
            user_message="It happens continuously on every part.",
            session_state=location_result["updated_state"],
        )
        final_result = await run_orchestrator(
            session_id="session-1",
            user_message="No parameters changed, but this is a new machine.",
            session_state=frequency_result["updated_state"],
        )

        self.assertEqual(final_result["step"], "awaiting_feedback")
        self.assertNotIn("one specific location", final_result["reply"])
        self.assertEqual(final_result["updated_state"]["diagnostic_stage"], "complete")
        location_answers = [
            pair for pair in final_result["updated_state"]["qa_pairs"]
            if pair["question"].startswith("Got it. Just one last detail")
        ]
        self.assertEqual(len(location_answers), 1)
        self.assertTrue(location_answers[0]["captured_early"])
        mock_text_defect_agent.assert_awaited_once()
        mock_rank_causes.assert_awaited_once()
        mock_generate_report.assert_awaited_once()

    async def test_frequency_and_changes_are_asked_separately(self):
        session_state = {
            "step": "questioning",
            "problem_description": "Hi",
            "qa_pairs": [],
            "pending_questions": [],
            "diagnostic_stage": "frequency",
            "workflow_started": True,
        }

        frequency_result = await run_orchestrator(
            session_id="session-1",
            user_message="It happens continuously on every part.",
            session_state=session_state,
        )

        self.assertEqual(
            frequency_result["updated_state"]["diagnostic_stage"],
            "changes",
        )
        self.assertIn("parameters or equipment", frequency_result["reply"])
        self.assertNotIn("one specific location", frequency_result["reply"])

        changes_result = await run_orchestrator(
            session_id="session-1",
            user_message="No parameters changed, but this is a new machine.",
            session_state=frequency_result["updated_state"],
        )

        self.assertEqual(
            changes_result["updated_state"]["diagnostic_stage"],
            "location",
        )
        self.assertIn("one specific location", changes_result["reply"])

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
            state["step"] = "awaiting_feedback"
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
            user_message="It happens across multiple locations.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "awaiting_feedback")
        self.assertIn("Undersized Dot", result["reply"])
        self.assertIn("Dispensing pressure is too low", result["reply"])
        self.assertIn("Did this fix the issue?", result["reply"])
        self.assertEqual(result["updated_state"]["defect_type"], "Undersized Dot")
        self.assertEqual(result["updated_state"]["step"], "awaiting_feedback")
        mock_text_defect_agent.assert_awaited_once()
        text_agent_call = mock_text_defect_agent.call_args.kwargs
        self.assertEqual(text_agent_call["problem_description"], "The dots are too small.")
        self.assertEqual(
            text_agent_call["qa_pairs"][-1]["answer"],
            "It happens across multiple locations.",
        )
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
            state["step"] = "awaiting_feedback"
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
            user_message="It happens across multiple locations after the nozzle change.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "awaiting_feedback")
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
            "project_id": 10,
            "knowledge_pack_id": 20,
            "knowledge_context": "Approved rule: low pressure can cause undersized dots.",
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
        mock_get_similar_cases.assert_awaited_once_with(
            "Undersized Dot",
            project_id=10,
            knowledge_pack_id=20,
        )

        call_args = mock_cause_ranking_agent.call_args
        self.assertEqual(call_args.kwargs["defect_type"], "Undersized Dot")
        self.assertIn("Defect identification summary", call_args.kwargs["problem_description"])
        self.assertEqual(call_args.kwargs["similar_cases"], mock_get_similar_cases.return_value)
        self.assertIn("Approved rule", call_args.kwargs["knowledge_context"])

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
            "project_id": 10,
            "knowledge_pack_id": 20,
            "knowledge_context": "Approved action: verify pressure.",
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="Generate report",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "awaiting_feedback")
        self.assertEqual(result["updated_state"]["step"], "awaiting_feedback")
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
        self.assertIn("Approved action", call_args.kwargs["knowledge_context"])

        save_call_args = mock_save_completed_case.call_args
        self.assertEqual(save_call_args.kwargs["session_id"], "session-1")
        self.assertEqual(save_call_args.kwargs["defect_type"], "Undersized Dot")
        self.assertEqual(save_call_args.kwargs["causes"], session_state["causes"])
        self.assertEqual(save_call_args.kwargs["project_id"], 10)
        self.assertEqual(save_call_args.kwargs["knowledge_pack_id"], 20)
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

        self.assertEqual(result["step"], "awaiting_feedback")
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

    async def test_natural_yes_feedback_records_outcome_and_action(self):
        session_state = {
            "step": "awaiting_feedback",
            "qa_pairs": [],
            "case_history_id": 123,
        }
        message = "Yes, reducing the dispensing pressure fixed the oversized dots."

        result = await run_orchestrator(
            session_id="session-1",
            user_message=message,
            session_state=session_state,
        )

        self.assertEqual(result["step"], "awaiting_feedback_cause")
        self.assertTrue(result["updated_state"]["feedback_fixed"])
        self.assertEqual(result["updated_state"]["feedback_action"], message)
        self.assertIn("root cause", result["reply"])

    async def test_plain_yes_still_requests_the_attempted_action(self):
        session_state = {
            "step": "awaiting_feedback",
            "qa_pairs": [],
            "case_history_id": 123,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="yes",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "awaiting_feedback_action")
        self.assertTrue(result["updated_state"]["feedback_fixed"])
        self.assertIn("Which recommended action", result["reply"])

    async def test_natural_negative_feedback_is_not_misread_as_positive(self):
        session_state = {
            "step": "awaiting_feedback",
            "qa_pairs": [],
            "case_history_id": 123,
        }

        result = await run_orchestrator(
            session_id="session-1",
            user_message="No, reducing the pressure did not fix the issue.",
            session_state=session_state,
        )

        self.assertEqual(result["step"], "awaiting_feedback_cause")
        self.assertFalse(result["updated_state"]["feedback_fixed"])
        self.assertIn("root cause", result["reply"])


if __name__ == "__main__":
    unittest.main()
