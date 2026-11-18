from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "fake"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    data_dir: Path = Path("data")
