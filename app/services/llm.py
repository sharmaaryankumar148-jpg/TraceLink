# Optional Gemini step for names/places/summary. Only runs if GEMINI_API_KEY is set.
# TODO: swap for a local model so complaint text never leaves the network
import logging

from pydantic import BaseModel, Field

from app.config import settings

log = logging.getLogger(__name__)


class LLMDetails(BaseModel):
    summary: str = Field(description="One sentence summary of the complaint for a police officer")
    suspect_names: list[str] = Field(default_factory=list, description="Names or aliases used by the suspect")
    locations: list[str] = Field(default_factory=list, description="Places mentioned")
    platforms: list[str] = Field(default_factory=list, description="Apps or websites used, e.g. WhatsApp, Telegram")
    language: str = Field(description="Language of the complaint: english, hindi or hinglish")


PROMPT = """You assist a police cyber cell. Read the complaint below and fill the schema.
Only use information written in the complaint. Do not guess. Leave lists empty if nothing is mentioned.

Complaint:
\"\"\"{text}\"\"\"
"""


def enrich(text: str) -> dict | None:
    if not settings.gemini_api_key:
        return None
    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=PROMPT.format(text=text),
            config={"response_mime_type": "application/json", "response_schema": LLMDetails},
        )
        return LLMDetails.model_validate_json(response.text).model_dump()
    except Exception as exc:
        log.warning("LLM enrichment skipped: %s", exc)
        return None
