"""
Image Defect ID Agent (Bonus 1) — Multimodal image-based defect identification.

Analyzes an uploaded dispensing defect image using GPT-4o's vision
capability to classify the defect type.

Model: GPT-4o (only agent that needs multimodal/vision — invoked only
       when a photo is actually uploaded to keep costs contained)
"""

import os
import base64
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "prompts", "image_defect_prompt.txt")

DEFECT_TYPES = [
    "Missing Dot",
    "Oversized Dot",
    "Undersized Dot",
    "Irregular Shape",
    "Excessive Spreading",
]


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


async def run(image_url: str | None = None, image_bytes: bytes | None = None) -> dict:
    """
    Identify defect type from an uploaded image.

    Args:
        image_url: URL of the image (from Supabase Storage)
        image_bytes: Raw image bytes (alternative to URL)

    Returns:
        dict with keys:
            defect_type: str — the identified defect type
            confidence: float — confidence score (0–1)
            reasoning: str — visual explanation of what was observed
            observations: list[str] — specific visual features noted

    TODO:
    - Load system prompt
    - Build multimodal message with image (URL or base64)
    - Call GPT-4o with vision
    - Parse structured output
    """
    return {
        "defect_type": "[Placeholder]",
        "confidence": 0.0,
        "reasoning": "[Placeholder] Image analysis not yet implemented.",
        "observations": [],
    }
