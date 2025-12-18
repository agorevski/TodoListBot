"""Centralized configuration and constants for the Discord A/B/C Todo Bot."""

from dataclasses import dataclass
from typing import Final

# Task validation constants
MAX_DESCRIPTION_LENGTH: Final[int] = 500
MIN_DESCRIPTION_LENGTH: Final[int] = 1

# Rate limiting constants
RATE_LIMIT_COMMANDS: Final[int] = 5
RATE_LIMIT_SECONDS: Final[float] = 10.0

# View/UI constants
VIEW_TIMEOUT_SECONDS: Final[float] = 300.0
MAX_BUTTONS_PER_VIEW: Final[int] = 25
BUTTONS_PER_ROW: Final[int] = 5

# Database constants
DEFAULT_DB_PATH: Final[str] = "data/tasks.db"
SCHEMA_VERSION: Final[int] = 2

# Connection retry settings
MAX_CONNECTION_RETRIES: Final[int] = 3
CONNECTION_RETRY_DELAY_SECONDS: Final[float] = 1.0

# Data retention settings (in days, 0 = disabled)
DEFAULT_RETENTION_DAYS: Final[int] = 0  # Disabled by default

# Auto-rollover settings
DEFAULT_ENABLE_AUTO_ROLLOVER: Final[bool] = True
ROLLOVER_HOUR_UTC: Final[int] = 0  # Midnight UTC


@dataclass(frozen=True)
class BotConfig:
    """Configuration container for bot settings.

    This dataclass holds runtime configuration that can be loaded
    from environment variables or other sources.
    """

    discord_token: str
    database_path: str = DEFAULT_DB_PATH
    log_level: str = "INFO"
    sync_commands_globally: bool = True
    retention_days: int = DEFAULT_RETENTION_DAYS
    enable_auto_rollover: bool = DEFAULT_ENABLE_AUTO_ROLLOVER

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Create a BotConfig from environment variables.

        Returns:
            BotConfig instance with values from environment

        Raises:
            ValueError: If DISCORD_TOKEN is not set
        """
        import os

        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError(
                "No Discord token provided. "
                "Set the DISCORD_TOKEN environment variable."
            )

        sync_env = os.getenv("SYNC_COMMANDS_GLOBALLY", "true")
        rollover_env = os.getenv("ENABLE_AUTO_ROLLOVER", "true")

        return cls(
            discord_token=token,
            database_path=os.getenv("DATABASE_PATH", DEFAULT_DB_PATH),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            sync_commands_globally=sync_env.lower() == "true",
            retention_days=int(
                os.getenv("RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))
            ),
            enable_auto_rollover=rollover_env.lower() == "true",
        )
