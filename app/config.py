"""Configuration management for Obsidian OpenAPI Server."""

import secrets
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server Configuration
    obsidian_openapi_port: int = Field(default=27150, alias="OBSIDIAN_OPENAPI_PORT")
    obsidian_openapi_host: str = Field(default="0.0.0.0", alias="OBSIDIAN_OPENAPI_HOST")

    # Obsidian REST API Configuration
    obsidian_api_url: str = Field(
        default="http://127.0.0.1:27123", alias="OBSIDIAN_API_URL"
    )
    obsidian_api_key: str = Field(..., alias="OBSIDIAN_API_KEY")

    # Server API Authentication
    server_api_key: Optional[str] = Field(default=None, alias="SERVER_API_KEY")

    # CORS Configuration - Use Union type to handle both string and list from env
    cors_origins: Union[str, List[str]] = Field(default="*", alias="CORS_ORIGINS")

    # Debug and Logging
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # History Configuration
    max_history_entries: int = Field(default=10, alias="MAX_HISTORY_ENTRIES")

    # Request Configuration
    request_timeout: float = Field(default=30.0, alias="REQUEST_TIMEOUT")

    # Security
    enable_key_regeneration: bool = Field(
        default=False, alias="ENABLE_KEY_REGENERATION"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins, str):
            if not self.cors_origins or self.cors_origins.strip() == "":
                return ["*"]
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()

    def generate_api_key(self) -> str:
        """Generate a cryptographically secure API key."""
        return secrets.token_urlsafe(32)

    def ensure_api_key(self) -> str:
        """Ensure an API key exists, generating one if necessary."""
        if not self.server_api_key:
            self.server_api_key = self.generate_api_key()
            # Persist to .env file
            self._persist_api_key(self.server_api_key)
        return self.server_api_key

    def _persist_api_key(self, api_key: str):
        """Persist the API key to the .env file."""
        env_path = Path(".env")
        if env_path.exists():
            content = env_path.read_text()
            if "SERVER_API_KEY=" in content:
                # Replace existing key
                lines = content.split("\n")
                new_lines = []
                for line in lines:
                    if line.startswith("SERVER_API_KEY="):
                        new_lines.append(f"SERVER_API_KEY={api_key}")
                    else:
                        new_lines.append(line)
                content = "\n".join(new_lines)
            else:
                # Add new key
                content += f"\nSERVER_API_KEY={api_key}\n"
            env_path.write_text(content)
        else:
            # Create new .env file
            env_path.write_text(f"SERVER_API_KEY={api_key}\n")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()