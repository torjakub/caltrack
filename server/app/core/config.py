from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:////data/caltrack.db"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    off_api_base_url: str = "https://world.openfoodfacts.org"
    usda_fdc_api_key: str = ""
    usda_fdc_base_url: str = "https://api.nal.usda.gov/fdc/v1"

    llm_provider: str = "none"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    openai_api_key: str = ""
    openai_model: str = ""

    ollama_host: str = "http://localhost:11434"
    ollama_text_model: str = ""
    ollama_vision_model: str = ""

    cohere_api_key: str = ""
    cohere_api_base_url: str = "https://api.cohere.com"
    cohere_text_model: str = "command-r-plus-08-2024"
    cohere_vision_model: str = "command-a-vision-07-2025"

    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()
