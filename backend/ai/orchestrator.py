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
    previous_answers = session_state.get("qa_pairs", [])

    if current_step == "questioning":
        # Call the Question Agent
        result = await run_question_agent(
            problem_description=user_message,
            previous_answers=previous_answers
        )
        
        if result.get("enough_info"):
            # Move to next phase if enough info
            current_step = "identifying"
            reply = "I think I have enough information now to identify the defect. Give me a moment to analyze."
        else:
            # Format questions out
            questions = result.get("questions", [])
            reply = "\n\n".join(questions) if questions else "Could you provide a bit more detail?"
            
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
