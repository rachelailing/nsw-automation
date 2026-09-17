"""
Image Defect ID Agent (Bonus 1) — Multimodal image-based defect identification.

Analyzes an uploaded dispensing defect image using GPT-4o's vision
capability to classify the defect type.

Model: GPT-4o (only agent that needs multimodal/vision — invoked only
       when a photo is actually uploaded to keep costs contained)
"""

import os
import base64
from pydantic import BaseModel, Field
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


class ImageDefectAgentResponse(BaseModel):
    defect_type: str
    confidence: float
    reasoning: str
    observations: list[str]
    likely_visible_symptoms: list[str] = Field(default_factory=list)
    unanswered_context_needed: list[str] = Field(default_factory=list)
    image_quality_notes: str = ""


def load_prompt() -> str:
    with open(PROMPT_FILE, "r") as f:
        return f.read()


def ensure_list(value) -> list[str]:
    return value if isinstance(value, list) else []


def ensure_string(value) -> str:
    return value if isinstance(value, str) else ""


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

    """
    if not image_url and not image_bytes:
        return {
            "defect_type": "Irregular Shape",
            "confidence": 0.0,
            "reasoning": "No image was provided for visual defect identification.",
            "observations": [],
            "likely_visible_symptoms": [],
            "unanswered_context_needed": [
                "material type",
                "defect frequency",
                "recent process or nozzle changes",
            ],
            "image_quality_notes": "No image available.",
        }

    system_prompt = load_prompt()

    if image_bytes:
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        image_content = {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encoded_image}"},
        }
    else:
        image_content = {
            "type": "image_url",
            "image_url": {"url": image_url},
        }

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Analyze this dispensing result image and identify the most likely "
                        "defect type from the known defect types. Also list the visual "
                        "symptoms the photo appears to answer and the process context that "
                        "still cannot be known from the image alone."
                    ),
                },
                image_content,
            ],
        },
    ]

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=messages,
            response_format=ImageDefectAgentResponse,
            temperature=0.1,
        )

        result = response.choices[0].message.parsed
        defect_type = result.defect_type.strip()

        if defect_type not in DEFECT_TYPES:
            defect_type = "Irregular Shape"

        confidence = max(0.0, min(1.0, result.confidence))

        return {
            "defect_type": defect_type,
            "confidence": confidence,
            "reasoning": result.reasoning,
            "observations": ensure_list(result.observations),
            "likely_visible_symptoms": ensure_list(result.likely_visible_symptoms),
            "unanswered_context_needed": ensure_list(result.unanswered_context_needed),
            "image_quality_notes": ensure_string(result.image_quality_notes),
        }
    except Exception as e:
        print(f"Error in Image Defect Agent: {e}")
        return {
            "defect_type": "Irregular Shape",
            "confidence": 0.2,
            "reasoning": "Unable to confidently classify the uploaded image, so this is a low-confidence fallback.",
            "observations": [],
            "likely_visible_symptoms": [],
            "unanswered_context_needed": [
                "material type",
                "defect frequency",
                "recent process or nozzle changes",
            ],
            "image_quality_notes": "Image analysis failed.",
        }
