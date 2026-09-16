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

    Args:
        session_id: Unique session identifier
        user_message: The user's latest message
        session_state: Current session state from Supabase (conversation_history, step, etc.)

    Returns:
        dict with keys: reply (str), step (str), updated_state (dict)

    TODO:
    - Load orchestrator system prompt
    - Determine current step from session_state
    - Call appropriate subagent(s)
    - Update session state
    - Return AI reply
    """
    current_step = session_state.get("step", "questioning")

    # Placeholder logic — replace with actual orchestrator implementation
    reply = f"[Orchestrator placeholder] Received: '{user_message}' | Current step: {current_step}"

    return {
        "reply": reply,
        "step": current_step,
        "updated_state": session_state,
    }
