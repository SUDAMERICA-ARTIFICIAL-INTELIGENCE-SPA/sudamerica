"""Configuration for open_agent microservice (Copiloto Administrativo — port 8005)."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from shared.utils.internal_service_auth import build_internal_service_trust_map
from shared.utils import validate_secret_length


class OpenAgentSettings(BaseSettings):
    """Settings loaded from environment variables."""

    # ── LLM Provider (uses a powerful model for admin reasoning) ──────
    LLM_PROVIDER: str = "openai"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.3

    # ── Inter-service ─────────────────────────────────────────────────
    SERVICE_API_EXECUTE_URL: str = "http://localhost:8000"

    FRONTEND_URL: str = "http://localhost:3000"

    # ── Auth ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_SERVICE_SECRET_KEY: str = Field(
        validation_alias="OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY",
    )
    API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY: str = ""
    INTERNAL_SERVICE_TOKEN_TTL_SECONDS: int = 300

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Tool call limits ──────────────────────────────────────────────
    MAX_TOOL_CALLS: int = 8

    @staticmethod
    def _normalize_provider(provider: str | None, default: str = "openai") -> str:
        normalized = (provider or default).strip().lower()
        return normalized or default

    def build_provider_config(self, provider: str | None = None) -> dict:
        """Resolve base_url, api_key, model for a provider."""
        resolved = self._normalize_provider(provider or self.LLM_PROVIDER)
        if resolved == "gemini":
            return {
                "provider": resolved,
                "base_url": self.GEMINI_BASE_URL,
                "api_key": self.GEMINI_API_KEY,
                "model": self.GEMINI_MODEL,
            }
        return {
            "provider": "openai",
            "base_url": self.OPENAI_BASE_URL,
            "api_key": self.OPENAI_API_KEY,
            "model": self.OPENAI_MODEL,
        }

    @property
    def provider_config(self) -> dict:
        return self.build_provider_config()

    @model_validator(mode="after")
    def _validate_security(self):
        self.JWT_SECRET_KEY = validate_secret_length(
            self.JWT_SECRET_KEY, "JWT_SECRET_KEY",
        )
        self.INTERNAL_SERVICE_SECRET_KEY = validate_secret_length(
            self.INTERNAL_SERVICE_SECRET_KEY,
            "OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY",
        )
        self.internal_service_trusted_keys
        return self

    @property
    def internal_service_trusted_keys(self) -> dict[str, str]:
        return build_internal_service_trust_map(
            service_name="open_agent",
            signing_key=self.INTERNAL_SERVICE_SECRET_KEY,
            trusted_keys={
                "api_execute": self.API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY,
            },
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }
