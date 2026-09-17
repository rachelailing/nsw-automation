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
from pydantic import BaseModel, Field
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "cause_ranking_prompt.txt")

CAUSE_CATEGORIES = [
    "Material Condition",
    "Air Bubbles",
    "Dispensing Parameters",
    "Nozzle Condition",
    "Equipment Condition",
]


class CauseItem(BaseModel):
    rank: int
    cause: str
    category: str
    confidence: float
    reasoning: str


class CauseRankingAgentResponse(BaseModel):
    causes: list[CauseItem] = Field(default_factory=list)


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


def format_rag_context(similar_cases: list[dict] | None) -> str:
    if not similar_cases:
        return "No similar past cases were provided."

    lines = []
    for idx, case in enumerate(similar_cases, 1):
        causes = case.get("causes") or []
        if isinstance(causes, list):
            cause_summary = "; ".join(
                cause.get("cause", str(cause)) if isinstance(cause, dict) else str(cause)
                for cause in causes[:3]
            )
        else:
            cause_summary = str(causes)

        lines.append(
            "\n".join(
                [
                    f"Case {idx}:",
                    f"- Problem: {case.get('problem_description', 'Not provided')}",
                    f"- Defect type: {case.get('defect_type', 'Not provided')}",
                    f"- Causes: {cause_summary or 'Not provided'}",
                    f"- Action plan: {case.get('action_plan', 'Not provided')}",
                    f"- Outcome: {case.get('outcome', 'Not provided')}",
                ]
            )
        )

    return "\n\n".join(lines)


def build_user_context(defect_type: str, problem_description: str, qa_pairs: list[dict]) -> str:
    context = (
        f"Identified Defect Type: {defect_type}\n\n"
        f"Initial Problem Description: {problem_description}\n\n"
    )

    if qa_pairs:
        context += "Questions and Answers:\n"
        for idx, qa in enumerate(qa_pairs, 1):
            context += f"Q{idx}. {qa.get('question', '')}\n"
            context += f"A{idx}. {qa.get('answer', '')}\n\n"
    else:
        context += "No follow-up Q&A was provided.\n\n"

    context += (
        "Generate 3 to 5 ranked likely root causes. Use the provided evidence "
        "and any similar past cases from the system prompt."
    )
    return context


def normalize_cause(item: CauseItem, rank: int) -> dict:
    category = item.category.strip()
    if category not in CAUSE_CATEGORIES:
        category = "Equipment Condition"

    return {
        "rank": rank,
        "cause": item.cause,
        "category": category,
        "confidence": max(0.0, min(1.0, item.confidence)),
        "reasoning": item.reasoning,
    }


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

    """
    rag_context = format_rag_context(similar_cases)
    system_prompt = load_prompt().replace("{rag_context}", rag_context)
    user_context = build_user_context(defect_type, problem_description, qa_pairs)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_context},
    ]

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=CauseRankingAgentResponse,
            temperature=0.2,
        )

        result = response.choices[0].message.parsed
        causes = [
            normalize_cause(item, rank)
            for rank, item in enumerate(result.causes[:5], 1)
        ]

        return {
            "causes": causes,
            "rag_context_used": bool(similar_cases),
        }
    except Exception as e:
        print(f"Error in Cause Ranking Agent: {e}")
        return {
            "causes": [
                {
                    "rank": 1,
                    "cause": "Incorrect dispensing pressure, time, speed, or dispense gap",
                    "category": "Dispensing Parameters",
                    "confidence": 0.4,
                    "reasoning": "Dispensing parameters are a common first check when reliable cause ranking is unavailable.",
                },
                {
                    "rank": 2,
                    "cause": "Nozzle clogging, worn nozzle tip, or wrong nozzle size",
                    "category": "Nozzle Condition",
                    "confidence": 0.3,
                    "reasoning": "Nozzle condition often directly affects dot size, shape, and consistency.",
                },
                {
                    "rank": 3,
                    "cause": "Material viscosity change, expired material, or trapped air",
                    "category": "Material Condition",
                    "confidence": 0.3,
                    "reasoning": "Material condition can cause inconsistent flow and visible dispensing defects.",
                },
            ],
            "rag_context_used": bool(similar_cases),
        }
