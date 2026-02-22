from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    model: str = "google/gemini-3-flash-preview"
    # model: str = "moonshotai/kimi-k2.5"
    # model: str = "anthropic/claude-3.5-haiku"
    # model: str = "google/gemini-2.5-flash"
    openrouter_api_key: str
    num_evaluations: int = 20
