"""Request/response schemas for AI narrative generation.

The AI feature only ever produces *narrative* text for the written business plan.
It never touches the financial calculation engine — project financials are read
(never written) purely to enrich the prompt with context.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Actions that transform text the user already has — these require ``current_text``.
_TEXT_ACTIONS = {"improve", "shorten", "expand", "translate_arabic", "translate_english"}

AiLanguage = Literal["english", "arabic"]
AiTone = Literal["investor", "bank", "formal", "government", "simple", "big_four"]
AiAction = Literal[
    "generate", "improve", "shorten", "expand", "translate_arabic", "translate_english"
]


class AiGenerateRequest(BaseModel):
    # Which narrative section this is for (either the stable key or the title).
    section_key: str | None = Field(default=None, max_length=200)
    section_title: str | None = Field(default=None, max_length=200)
    user_prompt: str = Field(default="", max_length=4000)
    language: AiLanguage = "english"
    tone: AiTone = "formal"
    action: AiAction = "generate"
    # The section's existing text — required for transform actions.
    current_text: str | None = Field(default=None, max_length=20000)

    @model_validator(mode="after")
    def _check_fields(self) -> "AiGenerateRequest":
        if not (self.section_key or self.section_title):
            raise ValueError("Provide section_key or section_title.")
        if self.action in _TEXT_ACTIONS and not (self.current_text or "").strip():
            raise ValueError(f"current_text is required for action '{self.action}'.")
        if self.action == "generate" and not (self.user_prompt or "").strip() \
                and not (self.section_title or "").strip():
            raise ValueError("Provide a user_prompt or section_title to generate from.")
        return self


class AiGenerateResponse(BaseModel):
    content: str
    language: AiLanguage
    action: AiAction
    provider: str
    model: str
