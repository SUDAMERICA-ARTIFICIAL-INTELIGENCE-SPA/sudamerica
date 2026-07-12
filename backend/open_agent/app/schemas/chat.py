"""Schemas for the admin copilot chat endpoint."""

from pydantic import BaseModel, Field


class FileAttachment(BaseModel):
    """File sent along with a chat message."""

    filename: str
    content_type: str  # e.g. image/png, application/pdf, text/csv
    data_base64: str  # base64-encoded file content


class SudamericaChatRequest(BaseModel):
    """Request from api_execute to the admin copilot."""

    system_prompt: str = Field(..., description="System prompt built by api_execute")
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[dict] = Field(
        default_factory=list,
        description="Recent conversation history [{role, content}]",
    )
    file: FileAttachment | None = Field(
        default=None,
        description="Optional file attachment (image, PDF, CSV)",
    )


class ToolUsage(BaseModel):
    name: str
    result_summary: str


class SudamericaChatResponse(BaseModel):
    """Response from the admin copilot."""

    response: str
    tokens_used: int = 0
    model_used: str = ""
    tools_used: list[ToolUsage] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    """Request from api_execute for pure text generation (NO tools).

    Serves the customer chat (WhatsApp) and the onboarding assistant. Same
    shape as SudamericaChatRequest, but the handler never exposes admin tools.
    """

    system_prompt: str = Field(..., description="System prompt built by api_execute")
    message: str = Field(..., min_length=1, max_length=8000)
    history: list[dict] = Field(
        default_factory=list,
        description="Recent conversation history [{role, content}]",
    )
    file: FileAttachment | None = Field(
        default=None,
        description="Optional file attachment (image, PDF, CSV)",
    )


class GenerateResponse(BaseModel):
    """Response for pure text generation (customer chat / onboarding)."""

    response: str
    tokens_used: int = 0
    model_used: str = ""
