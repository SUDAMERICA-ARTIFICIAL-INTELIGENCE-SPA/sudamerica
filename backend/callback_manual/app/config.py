"""Configuration for callback_manual microservice (Post-proceso / Revision Humana)."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from shared.utils.internal_service_auth import build_internal_service_trust_map
from shared.utils import validate_secret_length


class CallbackSettings(BaseSettings):
    """Settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sudamerica"

    # JWT (no default — must be set via env var)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    # OpenAI (Whisper transcription)
    OPENAI_API_KEY: str = ""

    # Internal service URLs
    SERVICE_API_EXECUTE_URL: str = "http://localhost:8000"
    SERVICE_TASKS_URL: str = "http://localhost:8003"
    INTERNAL_SERVICE_SECRET_KEY: str = Field(validation_alias="CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY")
    API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY: str = ""
    TASKS_INTERNAL_SERVICE_SECRET_KEY: str = ""
    CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY: str = ""
    INTERNAL_SERVICE_TOKEN_TTL_SECONDS: int = 300

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # Logging
    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def _validate_security(self):
        self.JWT_SECRET_KEY = validate_secret_length(self.JWT_SECRET_KEY, "JWT_SECRET_KEY")
        self.INTERNAL_SERVICE_SECRET_KEY = validate_secret_length(
            self.INTERNAL_SERVICE_SECRET_KEY,
            "CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY",
        )
        self.internal_service_trusted_keys
        return self

    @property
    def internal_service_trusted_keys(self) -> dict[str, str]:
        return build_internal_service_trust_map(
            service_name="callback_manual",
            signing_key=self.INTERNAL_SERVICE_SECRET_KEY,
            trusted_keys={
                "api_execute": self.API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY,
                "tasks": self.TASKS_INTERNAL_SERVICE_SECRET_KEY,
                "canales_service": self.CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY,
            },
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }
