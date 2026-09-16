"""
Report / Action Plan Agent (Steps 5–7) — Report formatting and action plan generation.

Takes the defect identification and cause ranking results and produces:
- A prioritized troubleshooting action plan (step-by-step checklist)
- A structured summary report
- Optionally triggers PDF generation (Bonus 4)

Model: GPT-4o-mini (mostly formatting — doesn't need a stronger model)
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "report_prompt.txt")


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


async def run(
    defect_type: str,
    causes: list[dict],
    problem_description: str,
    qa_pairs: list[dict],
) -> dict:
    """
    Generate the action plan and structured report.

    Args:
        defect_type: Identified defect type
        causes: Ranked causes from the Cause Ranking Agent
        problem_description: Original problem description
        qa_pairs: All Q&A from the session

    Returns:
        dict with keys:
            action_plan: list[dict] — ordered steps, each with:
                step_number: int
                action: str
                rationale: str
                priority: str (high/medium/low)
            summary: str — human-readable report summary
            recommendations: list[str] — preventive recommendations

    TODO:
    - Load system prompt
    - Build messages with all diagnosis context
    - Call GPT-4o-mini
    - Parse structured output
    """
    return {
        "action_plan": [],
        "summary": "[Placeholder] Report not yet generated.",
        "recommendations": [],
    }
