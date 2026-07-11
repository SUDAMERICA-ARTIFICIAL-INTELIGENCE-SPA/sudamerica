"""Configuration for api_execute microservice (Orquestador principal)."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from shared.utils.internal_service_auth import build_internal_service_trust_map
from shared.utils import validate_secret_length


class ApiExecuteSettings(BaseSettings):
    """Settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sudamerica"

    # JWT (no default — must be set via env var)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRATION_MINUTES: int = 30
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # Bcrypt
    BCRYPT_ROUNDS: int = 12

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PLUS: str = ""
    STRIPE_PRICE_PRO: str = ""

    # SaaS billing provider: "mercadopago" (CLP, default) or "stripe"
    PAYMENT_PROVIDER: str = "mercadopago"

    # Mercado Pago (suscripciones mensuales)
    MP_ACCESS_TOKEN: str = ""
    MP_WEBHOOK_SECRET: str = ""
    MP_API_BASE_URL: str = "https://api.mercadopago.com"
    MP_CURRENCY_ID: str = "CLP"
    # Precios web (sudamerica.ai): Crecimiento $29.990 / Corporativo $74.990 +IVA.
    # Confirmar si el cobro debe incluir IVA (override por env var).
    MP_PLAN_AMOUNT_PLUS: int = 29990
    MP_PLAN_AMOUNT_PRO: int = 74990

    # Internal service URLs
    SERVICE_AI_DIALER_URL: str = "http://localhost:8001"
    SERVICE_CALLBACK_URL: str = "http://localhost:8002"
    SERVICE_TASKS_URL: str = "http://localhost:8003"
    SERVICE_CANALES_URL: str = "http://localhost:8004"
    SERVICE_OPEN_AGENT_URL: str = "http://localhost:8005"

    # Firebase
    FIREBASE_PROJECT_ID: str = "siavanza-d9722"

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # Internal service auth
    INTERNAL_SERVICE_SECRET_KEY: str = Field(validation_alias="API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY")
    AI_DIALER_INTERNAL_SERVICE_SECRET_KEY: str = ""
    CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY: str = ""
    TASKS_INTERNAL_SERVICE_SECRET_KEY: str = ""
    CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY: str = ""
    OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY: str = ""
    INTERNAL_SERVICE_TOKEN_TTL_SECONDS: int = 300

    # LLM keys for menu import (AI extraction from PDF/images)
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # GCS media storage (shared bucket for all media: PDFs, images, audio)
    GCS_BUCKET_NAME: str = "sudamerica-media"
    GCS_PROJECT_ID: str = ""

    # Browserless.io (web scraping for URL menu import)
    BROWSERLESS_API_KEY: str = ""
    BROWSERLESS_TIMEOUT: int = 60

    # Evolution API (for WhatsApp group listing)
    EVOLUTION_API_URL: str = ""
    EVOLUTION_API_KEY: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    @model_validator(mode="after")
    def _validate_security(self):
        self.JWT_SECRET_KEY = validate_secret_length(self.JWT_SECRET_KEY, "JWT_SECRET_KEY")
        self.INTERNAL_SERVICE_SECRET_KEY = validate_secret_length(
            self.INTERNAL_SERVICE_SECRET_KEY,
            "API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY",
        )
        self.internal_service_trusted_keys
        return self

    @property
    def internal_service_trusted_keys(self) -> dict[str, str]:
        return build_internal_service_trust_map(
            service_name="api_execute",
            signing_key=self.INTERNAL_SERVICE_SECRET_KEY,
            trusted_keys={
                "ai_dialer": self.AI_DIALER_INTERNAL_SERVICE_SECRET_KEY,
                "callback_manual": self.CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY,
                "tasks": self.TASKS_INTERNAL_SERVICE_SECRET_KEY,
                "canales_service": self.CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY,
                "open_agent": self.OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY,
            },
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }
