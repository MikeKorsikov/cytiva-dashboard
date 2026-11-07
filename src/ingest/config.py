"""Settings and secrets, read from environment variables or a local .env file.

Nothing is hard-coded. Locally, values come from `.env` (gitignored).
In GitHub Actions and on a hosted app, values come from environment variables
or `.streamlit/secrets.toml`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


def load_env_file() -> None:
    """Load `.env` from the repo root if it exists. Existing environment variables win."""
    load_dotenv(REPO_ROOT / ".env", override=False)


def get_setting(name: str, *, required: bool = True) -> str | None:
    """Return a setting from the environment; raise a clear error if it is required and missing."""
    load_env_file()
    value = os.environ.get(name, "").strip()
    if not value:
        if required:
            raise ConfigError(
                f"Missing setting {name}. Add it to .env (see .env.example) "
                "or set it as an environment variable."
            )
        return None
    return value


def edgar_user_agent() -> str:
    """SEC EDGAR requires a User-Agent with a name and contact email on every request."""
    return get_setting("EDGAR_USER_AGENT")
