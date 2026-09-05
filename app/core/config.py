from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    firebase_project_id: str
    firebase_service_account_key_path: str | None = None
    firebase_app_name: str = "moovai"

    # AI provider — we call OpenAI's hosted REST API directly (no SDK), never
    # host or run a model ourselves. gpt-3.5-turbo is the default per product
    # requirements; override via OPENAI_MODEL for a different variant.
    openai_api_key: str
    openai_model: str = "gpt-3.5-turbo"

    # SerpApi — flight/hotel/destination search (Google Flights/Hotels/Search
    # engines). See app/services/search.py.
    serpapi_api_key: str

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
