from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Capacity AR API"
    app_env: str = "local"
    app_debug: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/capacity_ar"
    plan_generator: str = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    api_target: str = "/api"
    cors_origins: str | list[str] = [
        "http://localhost:5173",
        "https://capacity-ar.vercel.app",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    import json
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def normalize_render_postgres_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


settings = Settings()
