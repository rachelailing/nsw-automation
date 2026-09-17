"""
Main Orchestrator — Central conversation controller.

The orchestrator is the only "agent" the user talks to. It:
1. Manages the conversation state
2. Decides which subagent to call next based on the current step
3. Calls subagents as tool functions
4. Combines their outputs into coherent replies

Flow:
    Step 1 (Questioning)  → question_agent
    Step 2 (Defect ID)    → text_defect_agent (+ image_defect_agent if image uploaded)
    Step 3-4 (Cause Rank) → cause_ranking_agent (with RAG context from Supabase)
    Step 5-7 (Report)     → report_agent
"""

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import subagents
from ai.subagents.question_agent import run as run_question_agent
from ai.subagents.text_defect_agent import run as run_text_defect_agent
from ai.subagents.image_defect_agent import run as run_image_defect_agent
from ai.subagents.cause_ranking_agent import run as run_cause_ranking_agent
from ai.subagents.report_agent import run as run_report_agent


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(prompt_path, "r") as f:
        return f.read()


async def get_similar_cases(defect_type: str) -> list[dict]:
    """Lazy-load the database dependency only when cause ranking needs RAG."""
    from db.case_history import get_similar_cases as fetch_similar_cases

    return await fetch_similar_cases(defect_type)


PHOTO_ONLY_MESSAGES = {
    "",
    "image uploaded",
    "photo uploaded",
    "uploaded image",
    "uploaded photo",
    "[image uploaded]",
    "[photo uploaded]",
}


def has_meaningful_text(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() not in PHOTO_ONLY_MESSAGES


def format_image_context(image_result: dict | None) -> str:
    if not image_result:
        return ""

    observations = image_result.get("observations") or []
    visible_symptoms = image_result.get("likely_visible_symptoms") or []
    unknowns = image_result.get("unanswered_context_needed") or []

    return (
        "Uploaded Image Analysis:\n"
        f"- Preliminary defect type: {image_result.get('defect_type')}\n"
        f"- Confidence: {image_result.get('confidence')}\n"
        f"- Visual reasoning: {image_result.get('reasoning')}\n"
        f"- Observations: {', '.join(observations) if observations else 'none listed'}\n"
        f"- Symptoms already visible from photo: {', '.join(visible_symptoms) if visible_symptoms else 'none listed'}\n"
        f"- Context still needed from user: {', '.join(unknowns) if unknowns else 'none listed'}\n"
        f"- Image quality notes: {image_result.get('image_quality_notes', '')}"
    )


def build_question_context(problem_description: str, image_result: dict | None) -> str:
    parts = []

    if has_meaningful_text(problem_description):
        parts.append(f"User text description: {problem_description}")
    elif image_result:
        parts.append("User uploaded a defect photo first and has not provided a detailed text description yet.")

    image_context = format_image_context(image_result)
    if image_context:
        parts.append(image_context)
        parts.append(
            "Ask only for information that cannot be determined from the image, "
            "such as material, frequency, recent changes, equipment/nozzle, or process settings."
        )

    return "\n\n".join(parts) if parts else problem_description


def combine_defect_results(text_result: dict | None, image_result: dict | None = None) -> dict:
    """Merge text and image defect classifications into one decision."""
    if not text_result and image_result:
        return {
            **image_result,
            "source": "image",
            "text_result": None,
            "image_result": image_result,
        }

    if not image_result:
        return {
            **text_result,
            "source": "text",
            "text_result": text_result,
            "image_result": None,
        }

    text_confidence = text_result.get("confidence", 0.0)
    image_confidence = image_result.get("confidence", 0.0)
    text_type = text_result.get("defect_type")
    image_type = image_result.get("defect_type")

    if text_type == image_type:
        confidence = round(max(text_confidence, image_confidence), 2)
        reasoning = (
            f"Text and image analysis agree on {text_type}. "
            f"Text reasoning: {text_result.get('reasoning')} "
            f"Image reasoning: {image_result.get('reasoning')}"
        )
        chosen_type = text_type
        source = "text_and_image"
    elif image_confidence >= text_confidence + 0.15:
        confidence = image_confidence
        reasoning = (
            f"Image analysis is more confident than text analysis. "
            f"Image result: {image_type} because {image_result.get('reasoning')} "
            f"Text alternative: {text_type} because {text_result.get('reasoning')}"
        )
        chosen_type = image_type
        source = "image"
    else:
        confidence = text_confidence
        reasoning = (
            f"Text analysis is used as the primary result because it includes process context. "
            f"Text result: {text_type} because {text_result.get('reasoning')} "
            f"Image alternative: {image_type} because {image_result.get('reasoning')}"
        )
        chosen_type = text_type
        source = "text"

    return {
        "defect_type": chosen_type,
        "confidence": confidence,
        "reasoning": reasoning,
        "source": source,
        "text_result": text_result,
        "image_result": image_result,
    }


def build_ranking_problem_context(session_state: dict) -> str:
    problem_description = session_state.get("problem_description") or ""
    defect_result = session_state.get("defect_result") or {}
    image_result = session_state.get("image_result") or {}

    parts = []
    if has_meaningful_text(problem_description):
        parts.append(f"Problem description: {problem_description}")

    if defect_result:
        parts.append(
            "Defect identification summary:\n"
            f"- Defect type: {defect_result.get('defect_type')}\n"
            f"- Confidence: {defect_result.get('confidence')}\n"
            f"- Source: {defect_result.get('source')}\n"
            f"- Reasoning: {defect_result.get('reasoning')}"
        )

    if image_result:
        parts.append(format_image_context(image_result))

    return "\n\n".join(parts) if parts else "No problem description was provided."


def format_cause_ranking_reply(ranking_result: dict) -> str:
    causes = ranking_result.get("causes") or []
    if not causes:
        return "I could not generate ranked causes yet. Please provide more troubleshooting context."

    lines = [
        "Here are the most likely causes ranked by troubleshooting priority:",
        "",
    ]

    for cause in causes:
        lines.append(
            f"{cause.get('rank')}. {cause.get('cause')} "
            f"({cause.get('category')}, confidence {cause.get('confidence')})"
        )
        lines.append(f"   Reasoning: {cause.get('reasoning')}")

    if ranking_result.get("rag_context_used"):
        lines.append("")
        lines.append("I used similar past cases from the case history to inform this ranking.")

    lines.append("")
    lines.append("Next, this should flow into the troubleshooting action plan/report.")
    return "\n".join(lines)


def build_report_problem_context(session_state: dict) -> str:
    problem_description = session_state.get("problem_description") or ""
    defect_result = session_state.get("defect_result") or {}
    image_result = session_state.get("image_result") or {}

    parts = []
    if has_meaningful_text(problem_description):
        parts.append(f"Problem description: {problem_description}")

    if defect_result:
        parts.append(
            "Defect identification:\n"
            f"- Defect type: {defect_result.get('defect_type')}\n"
            f"- Confidence: {defect_result.get('confidence')}\n"
            f"- Source: {defect_result.get('source')}\n"
            f"- Reasoning: {defect_result.get('reasoning')}"
        )

    if image_result:
        parts.append(format_image_context(image_result))

    return "\n\n".join(parts) if parts else "No problem description was provided."


def format_report_reply(report: dict) -> str:
    lines = [
        "Troubleshooting report generated.",
        "",
        "Summary:",
        report.get("summary", ""),
    ]

    action_plan = report.get("action_plan") or []
    if action_plan:
        lines.extend(["", "Action plan:"])
        for step in action_plan:
            lines.append(
                f"{step.get('step_number')}. [{step.get('priority')}] {step.get('action')}"
            )
            lines.append(f"   Why: {step.get('rationale')}")

    recommendations = report.get("recommendations") or []
    if recommendations:
        lines.extend(["", "Preventive recommendations:"])
        for recommendation in recommendations:
            lines.append(f"- {recommendation}")

    return "\n".join(lines)


async def run_orchestrator(session_id: str, user_message: str, session_state: dict) -> dict:
    """
    Process a user message through the orchestrator.
    """
    current_step = session_state.get("step", "questioning")
    qa_pairs = session_state.get("qa_pairs", [])
    pending_questions = session_state.get("pending_questions", [])
    problem_description = session_state.get("problem_description", "")
    image_url = session_state.get("image_url")
    image_bytes = session_state.get("image_bytes")
    image_result = session_state.get("image_result")

    if (image_url or image_bytes) and not image_result:
        image_result = await run_image_defect_agent(
            image_url=image_url,
            image_bytes=image_bytes,
        )
        session_state["image_result"] = image_result

    if current_step == "questioning":
        if not problem_description and has_meaningful_text(user_message):
            problem_description = user_message
            session_state["problem_description"] = problem_description
        elif pending_questions:
            answered_question = pending_questions.pop(0)
            qa_pairs.append({
                "question": answered_question,
                "answer": user_message,
            })
            session_state["qa_pairs"] = qa_pairs
            session_state["pending_questions"] = pending_questions

            if pending_questions:
                return {
                    "reply": pending_questions[0],
                    "step": "questioning",
                    "updated_state": session_state,
                }

        # Call the Question Agent
        question_context = build_question_context(problem_description, image_result)
        result = await run_question_agent(
            problem_description=question_context,
            previous_answers=qa_pairs
        )
        
        if result.get("enough_info"):
            has_text_evidence = has_meaningful_text(problem_description) or bool(qa_pairs)

            if has_text_evidence and image_result and not session_state.get("text_result"):
                text_result = await run_text_defect_agent(
                    problem_description=problem_description or "Photo-first session with follow-up Q&A.",
                    qa_pairs=qa_pairs,
                )
                session_state["text_result"] = text_result
                defect_result = combine_defect_results(text_result, image_result)
            elif has_text_evidence and session_state.get("text_result"):
                defect_result = combine_defect_results(session_state["text_result"], image_result)
            elif has_text_evidence:
                text_result = await run_text_defect_agent(
                    problem_description=problem_description,
                    qa_pairs=qa_pairs,
                )
                session_state["text_result"] = text_result
                defect_result = combine_defect_results(text_result)
            elif image_result:
                defect_result = combine_defect_results(None, image_result)
            else:
                return {
                    "reply": "Please provide a problem description or upload a defect photo so I can begin the diagnosis.",
                    "step": "questioning",
                    "updated_state": session_state,
                }

            session_state["defect_result"] = defect_result
            session_state["defect_type"] = defect_result.get("defect_type")
            session_state["step"] = "ranking"

            reply = (
                "I have enough information to identify the likely defect.\n\n"
                f"Defect type: {defect_result.get('defect_type')}\n"
                f"Confidence: {defect_result.get('confidence')}\n\n"
                f"Source: {defect_result.get('source')}\n\n"
                f"Reasoning: {defect_result.get('reasoning')}\n\n"
                "Next, this should flow into cause ranking."
            )
            current_step = "ranking"
        else:
            # Format questions out
            questions = result.get("questions", [])
            session_state["pending_questions"] = questions
            reply = questions[0] if questions else "Could you provide a bit more detail?"
            current_step = "questioning"
            
        return {
            "reply": reply,
            "step": current_step,
            "updated_state": session_state,
        }

    if current_step == "ranking":
        defect_type = session_state.get("defect_type")
        if not defect_type:
            return {
                "reply": "I need to identify the defect type before ranking possible causes.",
                "step": "questioning",
                "updated_state": {**session_state, "step": "questioning"},
            }

        similar_cases = session_state.get("similar_cases")
        if similar_cases is None:
            similar_cases = await get_similar_cases(defect_type)
            session_state["similar_cases"] = similar_cases

        ranking_result = await run_cause_ranking_agent(
            defect_type=defect_type,
            problem_description=build_ranking_problem_context(session_state),
            qa_pairs=qa_pairs,
            similar_cases=similar_cases,
        )

        session_state["cause_ranking_result"] = ranking_result
        session_state["causes"] = ranking_result.get("causes", [])
        session_state["step"] = "reporting"

        return {
            "reply": format_cause_ranking_reply(ranking_result),
            "step": "reporting",
            "updated_state": session_state,
        }

    if current_step == "reporting":
        defect_type = session_state.get("defect_type")
        causes = session_state.get("causes") or []

        if not defect_type or not causes:
            return {
                "reply": "I need the defect type and ranked causes before generating the report.",
                "step": "ranking",
                "updated_state": {**session_state, "step": "ranking"},
            }

        report = await run_report_agent(
            defect_type=defect_type,
            causes=causes,
            problem_description=build_report_problem_context(session_state),
            qa_pairs=qa_pairs,
        )

        session_state["report"] = report
        session_state["step"] = "done"

        return {
            "reply": format_report_reply(report),
            "step": "done",
            "updated_state": session_state,
        }
        
    # Placeholder for other steps
    reply = f"[Orchestrator] Received: '{user_message}' | Current step is not wired yet."
    return {
        "reply": reply,
        "step": current_step,
        "updated_state": session_state,
    }
