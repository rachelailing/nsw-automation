"""
Cause Ranking Agent (Steps 3–4) — Cause generation, ranking, and scoring.

The most reasoning-heavy subagent. Given an identified defect type and
contextual information, it:
1. Queries Supabase for similar past cases (RAG)
2. Generates a ranked list of probable causes
3. Assigns confidence scores with reasoning

Cause categories from the challenge brief:
- Material condition
- Air bubbles
- Dispensing parameters
- Nozzle condition
- Equipment condition

Model: GPT-4o-mini (upgrade to GPT-4o if reasoning quality is insufficient)
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "cause_ranking_prompt.txt")


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


async def run(
    defect_type: str,
    problem_description: str,
    qa_pairs: list[dict],
    similar_cases: list[dict] | None = None,
) -> dict:
    """
    Generate ranked causes with confidence scores and reasoning.

    Args:
        defect_type: The identified defect type from Step 2
        problem_description: Original problem description
        qa_pairs: List of {question, answer} dicts
        similar_cases: Past cases retrieved from Supabase (RAG context)

    Returns:
        dict with keys:
            causes: list[dict] — ranked list of:
                cause: str
                category: str (material, air bubbles, parameters, nozzle, equipment)
                confidence: float (0–1)
                reasoning: str
            rag_context_used: bool — whether past cases were available

    TODO:
    - Load system prompt
    - Format RAG context (similar past cases) into prompt
    - Build messages with defect type + problem context
    - Call GPT-4o-mini (or GPT-4o)
    - Parse structured output
    """
    return {
        "causes": [],
        "rag_context_used": False,
    }
