"""Text extraction and structured draft generation for Knowledge Pack sources."""

import io
import json
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field


MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_EXTRACTED_CHARS = 60_000
SUPPORTED_EXTENSIONS = {".json", ".md", ".pdf", ".txt"}


class StrictExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MaterialDraft(StrictExtractionModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    material_type: str | None = None
    viscosity_min: float | None = None
    viscosity_max: float | None = None
    viscosity_unit: str | None = None
    handling_notes: str | None = None
    storage_conditions: str | None = None


class RuleConditions(StrictExtractionModel):
    frequency: str | None = None
    location: str | None = None
    recent_changes: str | None = None
    material: str | None = None
    parameter: str | None = None
    observations: list[str] = Field(default_factory=list)


class DefectRuleDraft(StrictExtractionModel):
    defect_type: str
    conditions: RuleConditions = Field(default_factory=RuleConditions)
    possible_cause: str
    category: str
    reasoning: str
    evidence_weight: float = Field(default=0.5, ge=0, le=1)


class TroubleshootingActionDraft(StrictExtractionModel):
    defect_type: str
    cause: str
    action: str
    sequence: int = Field(ge=1)
    safety_notes: str | None = None
    requires_approval: bool = False


class KnowledgeExtraction(StrictExtractionModel):
    materials: list[MaterialDraft] = Field(default_factory=list)
    defect_rules: list[DefectRuleDraft] = Field(default_factory=list)
    troubleshooting_actions: list[TroubleshootingActionDraft] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def extract_source_text(filename: str, content: bytes) -> tuple[str, str]:
    """Extract text from a supported source and return text plus source type."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Allowed extensions: {allowed}")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_SOURCE_BYTES:
        raise ValueError("The uploaded file exceeds the 5 MB limit.")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "PDF extraction requires pypdf. Run pip install -r backend/requirements.txt."
            ) from exc

        reader = PdfReader(io.BytesIO(content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc

    text = text.strip()
    if not text:
        raise ValueError("No readable text was found in the uploaded file.")
    return text[:MAX_EXTRACTED_CHARS], suffix.removeprefix(".")


def extract_structured_knowledge(text: str, source_type: str) -> dict:
    """Create a reviewable structured draft without modifying approved content."""
    if source_type == "json":
        try:
            parsed = KnowledgeExtraction.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                "JSON sources must match the Knowledge Pack extraction structure."
            ) from exc
        return parsed.model_dump(mode="json")

    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract only explicit dispensing-process knowledge from the source. "
                    "Do not infer missing limits, causes, actions, or safety requirements. "
                    "Return uncertain or incomplete statements in warnings instead of "
                    "turning them into authoritative records."
                ),
            },
            {
                "role": "user",
                "content": f"Source type: {source_type}\n\n{text}",
            },
        ],
        response_format=KnowledgeExtraction,
        temperature=0,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("The extraction model did not return structured content.")
    return parsed.model_dump(mode="json")
