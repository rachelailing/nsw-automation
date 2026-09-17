"""
Question Agent (Step 1) — Adaptive follow-up questioning.

Given an initial problem description from the user, generates up to ~5
targeted follow-up questions to gather enough information for defect
identification.

Model: GPT-4o-mini (simple, structured task — no need for a larger model)
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "question_prompt.txt")


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


from pydantic import BaseModel
import json

class QuestionAgentResponse(BaseModel):
    questions: list[str]
    enough_info: bool

async def run(problem_description: str, previous_answers: list[dict] | None = None) -> dict:
    """
    Generate adaptive follow-up questions based on the problem description
    and any answers already provided.

    Args:
        problem_description: The user's initial description of the dispensing problem
        previous_answers: List of {question, answer} dicts from earlier turns

    Returns:
        dict with keys:
            questions: list[str] — follow-up questions to ask
            enough_info: bool — True if we have enough info to proceed to defect ID
    """
    system_prompt = load_prompt()
    
    # Build conversation context
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    context = f"Initial Problem Description: {problem_description}\n\n"
    
    if previous_answers:
        context += "Previous Questions and Answers:\n"
        for idx, qa in enumerate(previous_answers, 1):
            context += f"Q{idx}. {qa.get('question', '')}\n"
            context += f"A{idx}. {qa.get('answer', '')}\n\n"
    
    context += "Based on the above, provide the next questions if more info is needed, or indicate enough info."
    
    messages.append({"role": "user", "content": context})
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=QuestionAgentResponse,
            temperature=0.2, # Low temperature for more deterministic/logical questions
        )
        
        result = response.choices[0].message.parsed
        return {
            "questions": result.questions if result.questions else [],
            "enough_info": result.enough_info
        }
    except Exception as e:
        print(f"Error in Question Agent: {e}")
        # Fallback to prevent breaking the flow
        return {
            "questions": ["Can you provide more details about the material and equipment you are using?"],
            "enough_info": False
        }
