"""Application settings loaded from the backend environment."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_HINDSIGHT_BANK_ID = "incidentiq-hackathon-demo"


@dataclass(frozen=True)
class Settings:
    """Central configuration. Secret fields are excluded from repr output."""

    hindsight_api_key: str | None = field(default=None, repr=False)
    hindsight_base_url: str = "https://api.hindsight.vectorize.io"
    hindsight_bank_id: str = DEFAULT_HINDSIGHT_BANK_ID
    groq_api_key: str | None = field(default=None, repr=False)
    groq_model: str = DEFAULT_GROQ_MODEL
    database_url: str | None = field(default=None, repr=False)

    @classmethod
    def load(cls) -> "Settings":
        """Load process environment, filling unset values from backend/.env."""
        load_dotenv(dotenv_path=ENV_FILE, override=False)
        return cls(
            hindsight_api_key=_optional_value("HINDSIGHT_API_KEY"),
            hindsight_base_url=(
                _optional_value("HINDSIGHT_BASE_URL")
                or "https://api.hindsight.vectorize.io"
            ),
            hindsight_bank_id=(
                _optional_value("HINDSIGHT_BANK_ID") or DEFAULT_HINDSIGHT_BANK_ID
            ),
            groq_api_key=_optional_value("GROQ_API_KEY"),
            groq_model=(
                _optional_value("GROQ_MODEL") or DEFAULT_GROQ_MODEL
            ),
            database_url=_optional_value("DATABASE_URL"),
        )

    def require_hindsight(self) -> tuple[str, str]:
        """Return Hindsight connection settings or fail without revealing values."""
        if not self.hindsight_api_key:
            raise RuntimeError("HINDSIGHT_API_KEY is required to initialize Hindsight.")
        if not self.hindsight_base_url:
            raise RuntimeError("HINDSIGHT_BASE_URL is required to initialize Hindsight.")
        return self.hindsight_base_url, self.hindsight_api_key

    def require_groq(self) -> str:
        """Return the Groq key when the Groq service is introduced."""
        if not self.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required to initialize Groq.")
        return self.groq_api_key

    def require_groq_model(self) -> str:
        """Return the configured Groq model ID, falling back to the documented default."""
        if not self.groq_model.strip():
            raise RuntimeError("GROQ_MODEL must be a non-empty model ID.")
        return self.groq_model.strip()

    def require_database(self) -> str:
        """Return the database URL when database access is introduced."""
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required to initialize the database.")
        return self.database_url


def _optional_value(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None
