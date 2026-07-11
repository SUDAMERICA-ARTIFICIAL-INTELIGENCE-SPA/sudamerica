"""Configuration for canales_service."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from shared.utils.internal_service_auth import build_internal_service_trust_map
from shared.utils import validate_secret_length


class CanalesSettings(BaseSettings):
    """Settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sudamerica"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    INTERNAL_SERVICE_SECRET_KEY: str = Field(validation_alias="CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY")
    API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY: str = ""
    AI_DIALER_INTERNAL_SERVICE_SECRET_KEY: str = ""
    CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY: str = ""
    TASKS_INTERNAL_SERVICE_SECRET_KEY: str = ""
    INTERNAL_SERVICE_TOKEN_TTL_SECONDS: int = 300

    EVOLUTION_API_URL: str = ""
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_WEBHOOK_URL: str = ""
    WEBHOOK_TOKEN: str = ""

    # WhatsApp Business Cloud API (Meta oficial)
    WA_BUSINESS_TOKEN_WEBHOOK: str = ""

    # Proxy para Baileys (evita bloqueo IP de datacenter)
    WA_PROXY_HOST: str = ""
    WA_PROXY_PORT: str = ""
    WA_PROXY_PROTOCOL: str = "http"  # http, https, socks5
    WA_PROXY_USERNAME: str = ""
    WA_PROXY_PASSWORD: str = ""

    SERVICE_AI_DIALER_URL: str = "http://localhost:8001"
    SERVICE_API_EXECUTE_URL: str = "http://localhost:8000"
    SERVICE_TASKS_URL: str = "http://localhost:8003"
    FRONTEND_URL: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"

    # Cloud Tasks — async webhook processing
    USE_CLOUD_TASKS: bool = False
    GCP_PROJECT: str = "sudamerica-prod"
    GCP_LOCATION: str = "us-central1"
    CLOUD_TASKS_QUEUE: str = "whatsapp-webhooks"

    # Google Cloud Storage for media files (audio, images, PDFs, videos)
    GCS_BUCKET_NAME: str = "sudamerica-media"
    GCS_SIGNED_URL_EXPIRY_HOURS: int = 168  # 7 days

    @model_validator(mode="after")
    def _validate_security(self):
        self.JWT_SECRET_KEY = validate_secret_length(self.JWT_SECRET_KEY, "JWT_SECRET_KEY")
        self.INTERNAL_SERVICE_SECRET_KEY = validate_secret_length(
            self.INTERNAL_SERVICE_SECRET_KEY,
            "CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY",
        )
        self.internal_service_trusted_keys
        if self.EVOLUTION_WEBHOOK_URL and not self.WEBHOOK_TOKEN.strip():
            raise ValueError("WEBHOOK_TOKEN must be configured when EVOLUTION_WEBHOOK_URL is set")
        if self.WEBHOOK_TOKEN:
            self.WEBHOOK_TOKEN = validate_secret_length(self.WEBHOOK_TOKEN, "WEBHOOK_TOKEN")
        return self

    @property
    def internal_service_trusted_keys(self) -> dict[str, str]:
        return build_internal_service_trust_map(
            service_name="canales_service",
            signing_key=self.INTERNAL_SERVICE_SECRET_KEY,
            trusted_keys={
                "api_execute": self.API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY,
                "ai_dialer": self.AI_DIALER_INTERNAL_SERVICE_SECRET_KEY,
                "callback_manual": self.CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY,
                "tasks": self.TASKS_INTERNAL_SERVICE_SECRET_KEY,
            },
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }
