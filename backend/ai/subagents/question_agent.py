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

    TODO:
    - Load system prompt
    - Build messages with problem_description + previous_answers
    - Call GPT-4o-mini
    - Parse response into structured output
    """
    return {
        "questions": ["[Placeholder] What type of dispensing process are you using?"],
        "enough_info": False,
    }
