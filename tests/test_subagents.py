import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Fix for OpenAI client requiring API key during import
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

# Add backend directory to sys.path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from ai.subagents import question_agent

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

if __name__ == '__main__':
    unittest.main()

