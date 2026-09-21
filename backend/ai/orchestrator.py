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
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import subagents
from ai.subagents.question_agent import run as run_question_agent
from ai.subagents.text_defect_agent import run as run_text_defect_agent
from ai.subagents.image_defect_agent import run as run_image_defect_agent
from ai.subagents.cause_ranking_agent import run as run_cause_ranking_agent
from ai.subagents.report_agent import run as run_report_agent



def parse_fixed_response(message: str) -> bool | None:
    value = message.strip().lower()

    if value in {"no", "n", "not fixed", "did not work", "not resolved"}:
        return False

    if value in {"yes", "y", "fixed", "it worked", "resolved"}:
        return True

    return None


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(prompt_path, "r") as f:
        return f.read()


async def get_similar_cases(defect_type: str) -> list[dict]:
    """Lazy-load the database dependency only when cause ranking needs RAG."""
    from db.case_history import get_similar_cases as fetch_similar_cases

    return await fetch_similar_cases(defect_type)


async def save_completed_case(
    session_id: str,
    problem_description: str,
    defect_type: str,
    causes: list[dict],
    action_plan: str,
) -> dict:
    """Lazy-load the database dependency only when a session is complete."""
    from db.case_history import save_case

    return await save_case(
        session_id=session_id,
        problem_description=problem_description,
        defect_type=defect_type,
        causes=causes,
        action_plan=action_plan,
    )


async def build_reference_threshold_context(
    problem_description: str,
    qa_pairs: list[dict],
    defect_type: str | None = None,
) -> tuple[str, dict | None]:
    """Return formatted threshold checks when numeric parameters are present."""
    try:
        from db.reference_thresholds import (
            evaluate_reference_thresholds,
            format_threshold_context,
        )

        evaluation = await evaluate_reference_thresholds(
            problem_description=problem_description,
            qa_pairs=qa_pairs,
            defect_type=defect_type,
        )
        return format_threshold_context(evaluation), evaluation
    except Exception as e:
        print(f"Reference threshold check skipped: {e}")
        return "", None


PHOTO_ONLY_MESSAGES = {
    "",
    "image uploaded",
    "photo uploaded",
    "uploaded image",
    "uploaded photo",
    "[image uploaded]",
    "[photo uploaded]",
}

MATERIAL_QUESTION = (
    "Hey there! Ready to help you troubleshoot your dispensing defect.\n\n"
    "To kick things off, what kind of material are you dispensing right now "
    "(like solder paste, epoxy, or underfill)?"
)
DIAMETER_QUESTION = (
    "Is the dispensing amount or diameter currently coming out too large, too small, "
    "or having some other issue? Also, what is the exact measured diameter if you have it?"
)
FREQUENCY_QUESTION = (
    "Is this defect happening continuously on every part, or is it occasional and random?"
)
CHANGES_QUESTION = (
    "Have any parameters or equipment recently changed, such as pressure, dispensing time, "
    "nozzle size, material batch, or the dispensing machine?"
)
LOCATION_QUESTION = (
    "Got it. Just one last detail to make sure I have the full picture: is this happening "
    "at one specific location on the board, or across multiple locations?"
)


def has_meaningful_text(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() not in PHOTO_ONLY_MESSAGES


def normalize_answer(value: str) -> str:
    """Normalize an answer for duplicate detection."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def validate_diagnostic_answer(
    stage: str,
    answer: str,
    qa_pairs: list[dict],
) -> str | None:
    """Return a clarification message when an answer does not fit its stage."""
    normalized = normalize_answer(answer)
    previous_answers = {
        normalize_answer(qa.get("answer", ""))
        for qa in qa_pairs
        if qa.get("answer")
    }

    prompts = {
        "material": "Please tell me the material being dispensed, such as solder paste, epoxy, or underfill.",
        "diameter": DIAMETER_QUESTION,
        "frequency": FREQUENCY_QUESTION,
        "changes": CHANGES_QUESTION,
        "location": LOCATION_QUESTION,
    }

    if not normalized:
        return prompts.get(stage, "Could you clarify your answer?")

    if normalized in previous_answers:
        return (
            "That appears to repeat your previous answer, so I have not recorded it "
            f"for this step.\n\n{prompts.get(stage, 'Could you clarify your answer?')}"
        )

    if stage == "material":
        if normalized in {"hi", "hello", "hey", "help"}:
            return prompts[stage]

    if stage == "diameter":
        has_measurement = bool(
            re.search(
                r"\d+(?:\.\d+)?\s*(?:mm|micron|um)\b",
                answer.lower(),
            )
        )
        has_defect_description = any(
            phrase in normalized
            for phrase in (
                "too large",
                "too small",
                "oversized",
                "undersized",
                "missing",
                "irregular",
                "spreading",
            )
        )
        if not has_measurement and not has_defect_description:
            return prompts[stage]

    if stage == "frequency":
        has_frequency = any(
            phrase in normalized
            for phrase in (
                "continuous",
                "continuously",
                "every part",
                "every cycle",
                "occasional",
                "occasionally",
                "intermittent",
                "random",
                "sometimes",
            )
        )
        if not has_frequency:
            return (
                "I could not tell how often the defect occurs. "
                "Please answer continuous, occasional, or intermittent."
            )

    if stage == "changes":
        has_change_context = any(
            phrase in normalized
            for phrase in (
                "changed",
                "change",
                "unchanged",
                "no parameter",
                "did not change",
                "didnt change",
                "pressure",
                "dispensing time",
                "nozzle",
                "new machine",
            )
        )
        if not has_change_context:
            return (
                "I could not tell whether anything changed. Please name the changed setting "
                "or equipment, or reply that there were no changes."
            )

    if stage == "location":
        has_location = any(
            phrase in normalized
            for phrase in (
                "one location",
                "single location",
                "specific location",
                "multiple",
                "across",
                "all locations",
                "everywhere",
            )
        )
        if not has_location:
            return (
                "I could not determine the affected location from that answer.\n\n"
                f"{prompts[stage]}"
            )

    return None


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

    threshold_context = session_state.get("reference_threshold_context")
    if threshold_context:
        parts.append(threshold_context)

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

    threshold_context = session_state.get("reference_threshold_context")
    if threshold_context:
        parts.append(threshold_context)

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


def format_completed_diagnosis_reply(session_state: dict) -> str:
    """Format the single final response produced after questioning completes."""
    defect_result = session_state.get("defect_result") or {}
    causes = session_state.get("causes") or []
    report = session_state.get("report") or {}
    confidence = defect_result.get("confidence", 0)
    confidence_percent = round(confidence * 100) if confidence <= 1 else round(confidence)

    lines = [
        "1) Detected Defect & Confidence Score: "
        f"{defect_result.get('defect_type', 'Unknown')} ({confidence_percent}% Confidence)",
        "",
        "2) Probable Root Cause:",
    ]
    if causes:
        top_cause = causes[0]
        lines.append(top_cause.get("cause", "Unknown"))
        if top_cause.get("reasoning"):
            lines.append(top_cause["reasoning"])
    else:
        lines.append("No probable cause could be ranked from the available evidence.")

    action_plan = (report.get("action_plan") or [])[:3]
    if action_plan:
        lines.extend(["", "3) Recommended 3-step action plan:"])
        for step in action_plan:
            lines.append(f"- {step.get('action')}")

    lines.extend(["", "Did this fix the issue?"])
    return "\n".join(lines)


def format_diameter_threshold_feedback(evaluation: dict | None) -> str:
    """Explain the measured diameter against the fetched reference limits."""
    checks = (evaluation or {}).get("checks") or []
    diameter_check = next(
        (check for check in checks if check.get("parameter") == "diameter"),
        None,
    )
    if not diameter_check:
        return "Got it."

    measured = diameter_check["measured"]
    minimum = diameter_check["min"]
    maximum = diameter_check["max"]
    status = diameter_check["status"]

    if status == "below_min":
        return (
            f"Your measured {measured:.2f} mm is below the {minimum:.2f} mm minimum "
            "limit from the reference table, confirming an undersized/insufficient deposit."
        )
    if status == "above_max":
        return (
            f"Your measured {measured:.2f} mm is above the {maximum:.2f} mm maximum "
            "limit from the reference table, confirming an oversized/excessive deposit."
        )
    return (
        f"Your measured {measured:.2f} mm is within the reference range of "
        f"{minimum:.2f} to {maximum:.2f} mm."
    )


async def rank_causes(session_state: dict, qa_pairs: list[dict]) -> dict:
    """Run cause ranking and store its result in the session state."""
    defect_type = session_state.get("defect_type")
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
    return ranking_result


async def generate_report_and_save_case(
    session_id: str,
    session_state: dict,
    qa_pairs: list[dict],
) -> dict:
    """Generate the report, persist the completed case, and mark the session done."""
    defect_type = session_state.get("defect_type")
    causes = session_state.get("causes") or []
    report_context = build_report_problem_context(session_state)
    report = await run_report_agent(
        defect_type=defect_type,
        causes=causes,
        problem_description=report_context,
        qa_pairs=qa_pairs,
    )

    session_state["report"] = report
    session_state["step"] = "awaiting_feedback"

    if not session_state.get("case_history_saved"):
        saved_case = await save_completed_case(
            session_id=session_id,
            problem_description=report_context,
            defect_type=defect_type,
            causes=causes,
            action_plan=format_report_reply(report),
        )
        session_state["case_history_saved"] = True
        session_state["case_history_id"] = saved_case.get("id")

    return report


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
        if "diagnostic_stage" not in session_state:
            session_state["diagnostic_stage"] = "material"
            session_state["workflow_started"] = False
            session_state["qa_pairs"] = []
            session_state["pending_questions"] = []
            qa_pairs = session_state["qa_pairs"]
            pending_questions = session_state["pending_questions"]

        if not session_state.get("workflow_started"):
            session_state["workflow_started"] = True
            if has_meaningful_text(user_message):
                session_state["problem_description"] = user_message
            return {
                "reply": MATERIAL_QUESTION,
                "step": "questioning",
                "updated_state": session_state,
            }

        diagnostic_stage = session_state.get("diagnostic_stage", "material")
        if diagnostic_stage == "frequency_and_changes":
            diagnostic_stage = "frequency"
            session_state["diagnostic_stage"] = diagnostic_stage

        validation_message = validate_diagnostic_answer(
            diagnostic_stage,
            user_message,
            qa_pairs,
        )
        if validation_message:
            return {
                "reply": validation_message,
                "step": "questioning",
                "updated_state": session_state,
            }

        if diagnostic_stage == "material":
            qa_pairs.append({"question": MATERIAL_QUESTION, "answer": user_message})
            session_state["qa_pairs"] = qa_pairs
            session_state["diagnostic_stage"] = "diameter"
            return {
                "reply": f"Got it, {user_message.strip()}.\n\n{DIAMETER_QUESTION}",
                "step": "questioning",
                "updated_state": session_state,
            }

        if diagnostic_stage == "diameter":
            qa_pairs.append({"question": DIAMETER_QUESTION, "answer": user_message})
            session_state["qa_pairs"] = qa_pairs
            threshold_context, threshold_evaluation = await build_reference_threshold_context(
                problem_description=problem_description,
                qa_pairs=qa_pairs,
            )
            if threshold_context:
                session_state["reference_threshold_context"] = threshold_context
                session_state["reference_threshold_evaluation"] = threshold_evaluation
            session_state["diagnostic_stage"] = "frequency"
            feedback = format_diameter_threshold_feedback(threshold_evaluation)
            return {
                "reply": f"{feedback}\n\n{FREQUENCY_QUESTION}",
                "step": "questioning",
                "updated_state": session_state,
            }

        if diagnostic_stage == "frequency":
            qa_pairs.append({
                "question": FREQUENCY_QUESTION,
                "answer": user_message,
            })
            session_state["qa_pairs"] = qa_pairs
            session_state["diagnostic_stage"] = "changes"
            return {
                "reply": CHANGES_QUESTION,
                "step": "questioning",
                "updated_state": session_state,
            }

        if diagnostic_stage == "changes":
            qa_pairs.append({
                "question": CHANGES_QUESTION,
                "answer": user_message,
            })
            session_state["qa_pairs"] = qa_pairs
            session_state["diagnostic_stage"] = "location"
            return {
                "reply": LOCATION_QUESTION,
                "step": "questioning",
                "updated_state": session_state,
            }

        if diagnostic_stage == "location":
            qa_pairs.append({"question": LOCATION_QUESTION, "answer": user_message})
            session_state["qa_pairs"] = qa_pairs
            session_state["diagnostic_stage"] = "complete"
            result = {"questions": [], "enough_info": True}
        else:
            result = {"questions": [], "enough_info": True}

        if not problem_description and has_meaningful_text(user_message):
            problem_description = user_message
            session_state["problem_description"] = problem_description
        
        if result.get("enough_info"):
            has_text_evidence = has_meaningful_text(problem_description) or bool(qa_pairs)
            threshold_context = ""

            if has_text_evidence and not session_state.get("reference_threshold_evaluation"):
                threshold_context, threshold_evaluation = await build_reference_threshold_context(
                    problem_description=problem_description,
                    qa_pairs=qa_pairs,
                )
                if threshold_context:
                    session_state["reference_threshold_context"] = threshold_context
                    session_state["reference_threshold_evaluation"] = threshold_evaluation
            else:
                threshold_context = session_state.get("reference_threshold_context", "")

            text_problem_description = problem_description
            if threshold_context:
                text_problem_description = (
                    f"{problem_description}\n\n{threshold_context}"
                )

            if has_text_evidence and image_result and not session_state.get("text_result"):
                text_result = await run_text_defect_agent(
                    problem_description=text_problem_description or "Photo-first session with follow-up Q&A.",
                    qa_pairs=qa_pairs,
                )
                session_state["text_result"] = text_result
                defect_result = combine_defect_results(text_result, image_result)
            elif has_text_evidence and session_state.get("text_result"):
                defect_result = combine_defect_results(session_state["text_result"], image_result)
            elif has_text_evidence:
                text_result = await run_text_defect_agent(
                    problem_description=text_problem_description,
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
            await rank_causes(session_state, qa_pairs)
            await generate_report_and_save_case(session_id, session_state, qa_pairs)
            reply = format_completed_diagnosis_reply(session_state)
            current_step = "awaiting_feedback"
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

        ranking_result = await rank_causes(session_state, qa_pairs)
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

        report = await generate_report_and_save_case(
            session_id,
            session_state,
            qa_pairs,
        )

        return {
            "reply": format_report_reply(report),
            "step": "awaiting_feedback",
            "updated_state": session_state,
        }
    if current_step == "awaiting_feedback":
        fixed = parse_fixed_response(user_message)

        if fixed is None:
            return {
                "reply": "Please answer yes or no: did the recommended action fix the issue?",
                "step": "awaiting_feedback",
                "updated_state": session_state,
            }

        session_state["feedback_fixed"] = fixed
        session_state["step"] = "awaiting_feedback_action"

        return {
            "reply": "Which recommended action did you try?",
            "step": "awaiting_feedback_action",
            "updated_state": session_state,
        }

    if current_step == "awaiting_feedback_action":
        session_state["feedback_action"] = user_message.strip()
        session_state["step"] = "awaiting_feedback_cause"

        return {
            "reply": "What root cause did this confirm? Say 'unknown' if it is not confirmed yet.",
            "step": "awaiting_feedback_cause",
            "updated_state": session_state,
        }

    if current_step == "awaiting_feedback_cause":
        from db.case_feedback import save_case_feedback

        cause = user_message.strip()
        if cause.lower() in {"unknown", "none", "not sure"}:
            cause = None

        await save_case_feedback(
            case_id=session_state["case_history_id"],
            session_id=session_id,
            fixed=session_state["feedback_fixed"],
            attempted_action=session_state["feedback_action"],
            confirmed_cause=cause,
        )

        session_state["feedback_saved"] = True
        session_state["step"] = "closed"

        return {
            "reply": "Thank you. The outcome has been saved for future troubleshooting cases.",
            "step": "closed",
            "updated_state": session_state,
        }
        
    # Placeholder for other steps
    reply = f"[Orchestrator] Received: '{user_message}' | Current step is not wired yet."
    return {
        "reply": reply,
        "step": current_step,
        "updated_state": session_state,
    }
