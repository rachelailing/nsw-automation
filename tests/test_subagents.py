import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Fix for OpenAI client requiring API key during import
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

# Add backend directory to sys.path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from ai.subagents import question_agent, text_defect_agent, image_defect_agent, cause_ranking_agent

class TestQuestionAgent(unittest.IsolatedAsyncioTestCase):

    @patch('ai.subagents.question_agent.client')
    async def test_run_generates_questions(self, mock_openai_client):
        # Setup mock response
        mock_parsed = MagicMock()
        mock_parsed.questions = ["Has the material expired?", "What is the ambient temperature?"]
        mock_parsed.enough_info = False
        
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        
        mock_openai_client.beta.chat.completions.parse.return_value = mock_response

        # Execute
        result = await question_agent.run(problem_description="The dots are too small and inconsistent.")

        # Assert
        self.assertIn("questions", result)
        self.assertEqual(len(result["questions"]), 2)
        self.assertFalse(result["enough_info"])
        mock_openai_client.beta.chat.completions.parse.assert_called_once()
        
    @patch('ai.subagents.question_agent.client')
    async def test_run_with_previous_answers(self, mock_openai_client):
        mock_parsed = MagicMock()
        mock_parsed.questions = []
        mock_parsed.enough_info = True
        
        mock_message = MagicMock()
        mock_message.parsed = mock_parsed
        mock_openai_client.beta.chat.completions.parse.return_value = MagicMock(choices=[MagicMock(message=mock_message)])

        previous_answers = [
            {"question": "Has the material expired?", "answer": "No, it is brand new."},
            {"question": "What is the ambient temperature?", "answer": "25 degrees Celsius, no recent change."}
        ]

        result = await question_agent.run(
            problem_description="The dots are too small.",
            previous_answers=previous_answers
        )

        self.assertIn("questions", result)
        self.assertTrue(result["enough_info"])
        
        # Verify the context included previous answers
        call_args = mock_openai_client.beta.chat.completions.parse.call_args
        called_messages = call_args.kwargs['messages']
        user_message_content = called_messages[1]['content']
        self.assertIn("Has the material expired?", user_message_content)
        self.assertIn("25 degrees Celsius", user_message_content)


class TestTextDefectAgent(unittest.IsolatedAsyncioTestCase):

    @patch('ai.subagents.text_defect_agent.client')
    async def test_run_identifies_defect_type(self, mock_openai_client):
        mock_parsed = MagicMock()
        mock_parsed.defect_type = "Undersized Dot"
        mock_parsed.confidence = 0.86
        mock_parsed.reasoning = "The user reports dots are smaller than target size."

        mock_message = MagicMock()
        mock_message.parsed = mock_parsed

        mock_openai_client.beta.chat.completions.parse.return_value = MagicMock(
            choices=[MagicMock(message=mock_message)]
        )

        qa_pairs = [
            {"question": "Is the dispensing amount too large or too small?", "answer": "Too small."},
            {"question": "Is it continuous or occasional?", "answer": "Continuous."},
        ]

        result = await text_defect_agent.run(
            problem_description="Glue dots are smaller than expected.",
            qa_pairs=qa_pairs,
        )

        self.assertEqual(result["defect_type"], "Undersized Dot")
        self.assertEqual(result["confidence"], 0.86)
        self.assertIn("smaller", result["reasoning"])
        mock_openai_client.beta.chat.completions.parse.assert_called_once()

        call_args = mock_openai_client.beta.chat.completions.parse.call_args
        called_messages = call_args.kwargs["messages"]
        user_message_content = called_messages[1]["content"]
        self.assertIn("Glue dots are smaller than expected.", user_message_content)
        self.assertIn("Too small.", user_message_content)

    @patch('ai.subagents.text_defect_agent.client')
    async def test_run_clamps_confidence_and_falls_back_for_unknown_defect(self, mock_openai_client):
        mock_parsed = MagicMock()
        mock_parsed.defect_type = "Unknown Defect"
        mock_parsed.confidence = 1.4
        mock_parsed.reasoning = "The symptoms do not map cleanly to the known list."

        mock_message = MagicMock()
        mock_message.parsed = mock_parsed

        mock_openai_client.beta.chat.completions.parse.return_value = MagicMock(
            choices=[MagicMock(message=mock_message)]
        )

        result = await text_defect_agent.run(
            problem_description="The output shape is strange.",
            qa_pairs=[],
        )

        self.assertEqual(result["defect_type"], "Irregular Shape")
        self.assertEqual(result["confidence"], 1.0)


class TestImageDefectAgent(unittest.IsolatedAsyncioTestCase):

    @patch('ai.subagents.image_defect_agent.client')
    async def test_run_identifies_defect_from_image_url(self, mock_openai_client):
        mock_parsed = MagicMock()
        mock_parsed.defect_type = "Excessive Spreading"
        mock_parsed.confidence = 0.91
        mock_parsed.reasoning = "The material spreads beyond the expected boundary."
        mock_parsed.observations = ["wide wetting area", "soft dot boundary"]

        mock_message = MagicMock()
        mock_message.parsed = mock_parsed

        mock_openai_client.beta.chat.completions.parse.return_value = MagicMock(
            choices=[MagicMock(message=mock_message)]
        )

        result = await image_defect_agent.run(image_url="https://example.com/defect.png")

        self.assertEqual(result["defect_type"], "Excessive Spreading")
        self.assertEqual(result["confidence"], 0.91)
        self.assertEqual(len(result["observations"]), 2)
        mock_openai_client.beta.chat.completions.parse.assert_called_once()

    async def test_run_without_image_returns_no_image_result(self):
        result = await image_defect_agent.run()

        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("No image", result["reasoning"])


class TestCauseRankingAgent(unittest.IsolatedAsyncioTestCase):

    @patch('ai.subagents.cause_ranking_agent.client')
    async def test_run_generates_ranked_causes_with_rag_context(self, mock_openai_client):
        cause_1 = MagicMock()
        cause_1.rank = 1
        cause_1.cause = "Dispensing pressure is set too low"
        cause_1.category = "Dispensing Parameters"
        cause_1.confidence = 0.55
        cause_1.reasoning = "The dots are consistently undersized, which points to insufficient dispense volume."

        cause_2 = MagicMock()
        cause_2.rank = 2
        cause_2.cause = "Nozzle is partially clogged"
        cause_2.category = "Nozzle Condition"
        cause_2.confidence = 0.3
        cause_2.reasoning = "A partial clog can restrict flow and reduce dot size."

        cause_3 = MagicMock()
        cause_3.rank = 3
        cause_3.cause = "Material viscosity has increased"
        cause_3.category = "Material Condition"
        cause_3.confidence = 0.15
        cause_3.reasoning = "Higher viscosity can reduce flow under the same pressure."

        mock_parsed = MagicMock()
        mock_parsed.causes = [cause_1, cause_2, cause_3]

        mock_message = MagicMock()
        mock_message.parsed = mock_parsed

        mock_openai_client.beta.chat.completions.parse.return_value = MagicMock(
            choices=[MagicMock(message=mock_message)]
        )

        similar_cases = [
            {
                "problem_description": "Small dots on Line 3",
                "defect_type": "Undersized Dot",
                "causes": [{"cause": "Low dispensing pressure"}],
                "action_plan": "Increase pressure and verify dot diameter.",
                "outcome": "Fixed",
            }
        ]

        result = await cause_ranking_agent.run(
            defect_type="Undersized Dot",
            problem_description="Glue dots are too small.",
            qa_pairs=[{"question": "Is it continuous?", "answer": "Yes, every cycle."}],
            similar_cases=similar_cases,
        )

        self.assertTrue(result["rag_context_used"])
        self.assertEqual(len(result["causes"]), 3)
        self.assertEqual(result["causes"][0]["rank"], 1)
        self.assertEqual(result["causes"][0]["category"], "Dispensing Parameters")

        call_args = mock_openai_client.beta.chat.completions.parse.call_args
        called_messages = call_args.kwargs["messages"]
        self.assertIn("Small dots on Line 3", called_messages[0]["content"])
        self.assertIn("Undersized Dot", called_messages[1]["content"])
        self.assertIn("Yes, every cycle.", called_messages[1]["content"])

    @patch('ai.subagents.cause_ranking_agent.client')
    async def test_run_normalizes_unknown_category_and_confidence(self, mock_openai_client):
        cause = MagicMock()
        cause.rank = 1
        cause.cause = "Unknown mechanical issue"
        cause.category = "Random Category"
        cause.confidence = 1.5
        cause.reasoning = "The evidence is unclear."

        mock_parsed = MagicMock()
        mock_parsed.causes = [cause]

        mock_message = MagicMock()
        mock_message.parsed = mock_parsed

        mock_openai_client.beta.chat.completions.parse.return_value = MagicMock(
            choices=[MagicMock(message=mock_message)]
        )

        result = await cause_ranking_agent.run(
            defect_type="Irregular Shape",
            problem_description="Dot shape is abnormal.",
            qa_pairs=[],
        )

        self.assertFalse(result["rag_context_used"])
        self.assertEqual(result["causes"][0]["category"], "Equipment Condition")
        self.assertEqual(result["causes"][0]["confidence"], 1.0)

if __name__ == '__main__':
    unittest.main()
