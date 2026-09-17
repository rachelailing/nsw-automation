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
from pydantic import BaseModel
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


class TextDefectAgentResponse(BaseModel):
    defect_type: str
    confidence: float
    reasoning: str


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

    """
    system_prompt = load_prompt()

    context = f"Initial Problem Description: {problem_description}\n\n"

    if qa_pairs:
        context += "Questions and Answers:\n"
        for idx, qa in enumerate(qa_pairs, 1):
            context += f"Q{idx}. {qa.get('question', '')}\n"
            context += f"A{idx}. {qa.get('answer', '')}\n\n"
    else:
        context += "No follow-up Q&A was provided.\n\n"

    context += (
        "Identify the most likely defect type from the known defect types. "
        "Return the defect type, confidence, and reasoning."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=TextDefectAgentResponse,
            temperature=0.1,
        )

        result = response.choices[0].message.parsed
        defect_type = result.defect_type.strip()

        if defect_type not in DEFECT_TYPES:
            defect_type = "Irregular Shape"

        confidence = max(0.0, min(1.0, result.confidence))

        return {
            "defect_type": defect_type,
            "confidence": confidence,
            "reasoning": result.reasoning,
        }
    except Exception as e:
        print(f"Error in Text Defect Agent: {e}")
        return {
            "defect_type": "Irregular Shape",
            "confidence": 0.2,
            "reasoning": "Unable to confidently classify the defect from text, so this is a low-confidence fallback.",
        }
