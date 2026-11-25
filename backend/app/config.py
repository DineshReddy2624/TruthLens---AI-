"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings with defaults for development."""

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = "truthlens"
    MYSQL_USER: str = "truthlens"
    MYSQL_PASSWORD: str = "changeme_in_production"

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret-key-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Ollama
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # ChromaDB
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000

    # Search
    SEARCH_PROVIDER: str = "tavily"
    SEARCH_API_KEY: str = ""

    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt"

    # Database URL override (e.g. for local dev without Docker)
    DATABASE_URL: str | None = None

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            # Handle relative sqlite URLs portably across any machine / OS
            if self.DATABASE_URL.startswith("sqlite:///"):
                path_str = self.DATABASE_URL[len("sqlite:///"):]
                p = Path(path_str)
                if not p.is_absolute():
                    resolved = (PROJECT_ROOT / path_str.lstrip("./")).resolve()
                    return f"sqlite:///{resolved.as_posix()}"
            return self.DATABASE_URL

        # Default portable fallback: if truthlens.db exists in project root, use it
        sqlite_file = PROJECT_ROOT / "truthlens.db"
        if sqlite_file.exists():
            return f"sqlite:///{sqlite_file.resolve().as_posix()}"

        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            "?charset=utf8mb4"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": [".env", "../.env"], "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
