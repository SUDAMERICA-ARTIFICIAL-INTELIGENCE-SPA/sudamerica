"""Schemas for onboarding chat endpoint."""

from pydantic import BaseModel, Field


class OnboardingMessage(BaseModel):
    role: str = Field(..., pattern="^(bot|user)$")
    text: str


class OnboardingChatRequest(BaseModel):
    messages: list[OnboardingMessage] = Field(default_factory=list)
    currentData: dict = Field(default_factory=dict)
    # Rubro elegido en el onboarding (F2 lo envía desde el selector). Opcional →
    # fail-safe a restaurante, por lo que el flujo actual no cambia.
    rubro: str | None = None


class OnboardingChatResponse(BaseModel):
    reply: str
    extractedData: dict = Field(default_factory=dict)
    complete: bool = False
    inputType: str = "text"
