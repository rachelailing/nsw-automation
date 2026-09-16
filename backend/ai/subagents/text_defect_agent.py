"""
Text Defect ID Agent (Step 2) — Text-based defect identification.

Analyzes the gathered Q&A information to classify the most likely
dispensing defect type from the known categories:
- Missing Dot
- Oversized Dot
- Undersized Dot
- Irregular Shape
- Excessive Spreading

Model: GPT-4o-mini (classification task against a known list)
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "text_defect_prompt.txt")

# Known defect categories from the challenge brief
DEFECT_TYPES = [
    "Missing Dot",
    "Oversized Dot",
    "Undersized Dot",
    "Irregular Shape",
    "Excessive Spreading",
]


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


async def run(problem_description: str, qa_pairs: list[dict]) -> dict:
    """
    Identify the most likely defect type from text information.

    Args:
        problem_description: Original problem description
        qa_pairs: List of {question, answer} dicts from the questioning step

    Returns:
        dict with keys:
            defect_type: str — the identified defect type
            confidence: float — confidence score (0–1)
            reasoning: str — explanation of why this defect was identified

    TODO:
    - Load system prompt
    - Build messages with problem context + Q&A answers
    - Call GPT-4o-mini with structured output
    - Parse and return
    """
    return {
        "defect_type": "[Placeholder]",
        "confidence": 0.0,
        "reasoning": "[Placeholder] Not yet implemented.",
    }
