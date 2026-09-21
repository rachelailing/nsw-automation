"""
Report / Action Plan Agent (Steps 5–7) — Report formatting and action plan generation.

Takes the defect identification and cause ranking results and produces:
- A prioritized troubleshooting action plan (step-by-step checklist)
- A structured summary report
- Optionally triggers PDF generation (Bonus 4)

Model: GPT-4o-mini (mostly formatting — doesn't need a stronger model)
"""

import os
from pydantic import BaseModel, Field
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "report_prompt.txt")

PRIORITIES = {"high", "medium", "low"}


class ActionPlanStep(BaseModel):
    step_number: int
    action: str
    rationale: str
    priority: str


class ReportAgentResponse(BaseModel):
    summary: str
    action_plan: list[ActionPlanStep] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


def build_report_context(
    defect_type: str,
    causes: list[dict],
    problem_description: str,
    qa_pairs: list[dict],
) -> str:
    context = (
        f"Identified Defect Type: {defect_type}\n\n"
        f"Problem Description:\n{problem_description}\n\n"
    )

    if qa_pairs:
        context += "Diagnostic Questions and Answers:\n"
        for idx, qa in enumerate(qa_pairs, 1):
            context += f"Q{idx}. {qa.get('question', '')}\n"
            context += f"A{idx}. {qa.get('answer', '')}\n\n"
    else:
        context += "No diagnostic Q&A was provided.\n\n"

    if causes:
        context += "Ranked Possible Causes:\n"
        for cause in causes:
            context += (
                f"{cause.get('rank', '')}. {cause.get('cause', '')}\n"
                f"   Category: {cause.get('category', '')}\n"
                f"   Confidence: {cause.get('confidence', '')}\n"
                f"   Reasoning: {cause.get('reasoning', '')}\n\n"
            )
    else:
        context += "No ranked causes were provided.\n\n"

    context += (
        "Generate a technician-facing troubleshooting report with a concise summary, "
        "an ordered action checklist, and preventive recommendations."
    )
    return context


def normalize_priority(priority: str) -> str:
    priority = (priority or "").strip().lower()
    return priority if priority in PRIORITIES else "medium"


def normalize_action_step(step: ActionPlanStep, step_number: int) -> dict:
    return {
        "step_number": step_number,
        "action": step.action,
        "rationale": step.rationale,
        "priority": normalize_priority(step.priority),
    }


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

    """
    system_prompt = load_prompt()
    user_context = build_report_context(
        defect_type=defect_type,
        causes=causes,
        problem_description=problem_description,
        qa_pairs=qa_pairs,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_context},
    ]

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=ReportAgentResponse,
            temperature=0.2,
        )

        result = response.choices[0].message.parsed
        action_plan = [
            normalize_action_step(step, idx)
            for idx, step in enumerate(result.action_plan[:3], 1)
        ]

        return {
            "action_plan": action_plan,
            "summary": result.summary,
            "recommendations": result.recommendations[:3],
        }
    except Exception as e:
        print(f"Error in Report Agent: {e}")
        top_cause = causes[0] if causes else {}
        return {
            "action_plan": [
                {
                    "step_number": 1,
                    "action": "Review the top-ranked cause and verify the related machine settings.",
                    "rationale": f"Top suspected cause: {top_cause.get('cause', 'not available')}.",
                    "priority": "high",
                },
                {
                    "step_number": 2,
                    "action": "Inspect the nozzle and material path for blockage, wear, or residue.",
                    "rationale": "Nozzle and material path issues commonly affect dispensing size and shape.",
                    "priority": "medium",
                },
                {
                    "step_number": 3,
                    "action": "Record the final confirmed cause and successful fix.",
                    "rationale": "Saving the outcome improves future troubleshooting recommendations.",
                    "priority": "low",
                },
            ],
            "summary": f"{defect_type} was identified, but the report agent could not generate a full report.",
            "recommendations": [
                "Keep a record of confirmed causes and corrective actions for each case.",
                "Review dispensing parameters and nozzle condition during regular maintenance.",
            ],
        }
