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


async def run_orchestrator(session_id: str, user_message: str, session_state: dict) -> dict:
    """
    Process a user message through the orchestrator.
    """
    current_step = session_state.get("step", "questioning")
    qa_pairs = session_state.get("qa_pairs", [])
    pending_questions = session_state.get("pending_questions", [])
    problem_description = session_state.get("problem_description", "")

    if current_step == "questioning":
        if not problem_description:
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
        result = await run_question_agent(
            problem_description=problem_description,
            previous_answers=qa_pairs
        )
        
        if result.get("enough_info"):
            defect_result = await run_text_defect_agent(
                problem_description=problem_description,
                qa_pairs=qa_pairs,
            )

            session_state["defect_result"] = defect_result
            session_state["defect_type"] = defect_result.get("defect_type")
            session_state["step"] = "ranking"

            reply = (
                "I have enough information to identify the likely defect.\n\n"
                f"Defect type: {defect_result.get('defect_type')}\n"
                f"Confidence: {defect_result.get('confidence')}\n\n"
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
        
    # Placeholder for other steps
    reply = f"[Orchestrator] Received: '{user_message}' | Current step is not wired yet."
    return {
        "reply": reply,
        "step": current_step,
        "updated_state": session_state,
    }
