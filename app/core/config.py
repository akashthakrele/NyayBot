"""
app/core/config.py — Application settings via Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration.  Values are read from environment variables
    (or a .env file automatically via pydantic-settings).
    """

    PROJECT_NAME: str = "NyayBot"
    GITHUB_TOKEN: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
