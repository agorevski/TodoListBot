"""Centralized configuration and constants for the Discord A/B/C Todo Bot."""

from dataclasses import dataclass
from typing import Final

from .exceptions import ConfigurationError

# Task validation constants
MAX_DESCRIPTION_LENGTH: Final[int] = 500
MIN_DESCRIPTION_LENGTH: Final[int] = 1

# Rate limiting constants
RATE_LIMIT_COMMANDS: Final[int] = 5
RATE_LIMIT_SECONDS: Final[float] = 10.0

# View/UI constants
# Discord limits interactive message components (Views) to:
# - Maximum 5 action rows per message
# - Maximum 5 buttons per action row
# - Therefore: 5 rows × 5 buttons = 25 maximum buttons per view
VIEW_TIMEOUT_SECONDS: Final[float] = 300.0  # 5 minutes before view expires
MAX_BUTTONS_PER_VIEW: Final[int] = 25  # Discord limit: 5 rows × 5 buttons
BUTTONS_PER_ROW: Final[int] = 5  # Discord limit: max 5 buttons per action row

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
DEFAULT_ROLLOVER_HOUR_UTC: Final[int] = 0  # Midnight UTC


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
    rollover_hour_utc: int = DEFAULT_ROLLOVER_HOUR_UTC

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Create a BotConfig from environment variables.

        Reads configuration values from environment variables and constructs
        a BotConfig instance. Uses default values for any unset optional
        environment variables.

        Environment Variables:
            DISCORD_TOKEN: Required. The Discord bot token for authentication.
            DATABASE_PATH: Optional. Path to the SQLite database file.
                Defaults to "data/tasks.db".
            LOG_LEVEL: Optional. Logging level (DEBUG, INFO, WARNING, ERROR).
                Defaults to "INFO".
            SYNC_COMMANDS_GLOBALLY: Optional. Whether to sync slash commands
                globally. Defaults to "true".
            RETENTION_DAYS: Optional. Number of days to retain completed tasks.
                Defaults to 0 (disabled).
            ENABLE_AUTO_ROLLOVER: Optional. Whether to enable automatic task
                rollover. Defaults to "true".
            ROLLOVER_HOUR_UTC: Optional. Hour (0-23) in UTC for daily rollover.
                Defaults to 0 (midnight UTC).

        Returns:
            BotConfig: A new BotConfig instance populated with values from
                environment variables.

        Raises:
            ConfigurationError: If DISCORD_TOKEN is not set or if
                ROLLOVER_HOUR_UTC is not a valid integer between 0 and 23.
        """
        import os

        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ConfigurationError(
                "No Discord token provided. "
                "Set the DISCORD_TOKEN environment variable."
            )

        sync_env = os.getenv("SYNC_COMMANDS_GLOBALLY", "true")
        rollover_env = os.getenv("ENABLE_AUTO_ROLLOVER", "true")

        # Parse rollover hour with validation
        rollover_hour_str = os.getenv(
            "ROLLOVER_HOUR_UTC", str(DEFAULT_ROLLOVER_HOUR_UTC)
        )
        try:
            rollover_hour = int(rollover_hour_str)
            if not 0 <= rollover_hour <= 23:
                raise ConfigurationError(
                    f"ROLLOVER_HOUR_UTC must be between 0 and 23, got {rollover_hour}"
                )
        except ValueError as e:
            raise ConfigurationError(
                f"ROLLOVER_HOUR_UTC must be a valid integer, got '{rollover_hour_str}'"
            ) from e

        return cls(
            discord_token=token,
            database_path=os.getenv("DATABASE_PATH", DEFAULT_DB_PATH),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            sync_commands_globally=sync_env.lower() == "true",
            retention_days=int(
                os.getenv("RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))
            ),
            enable_auto_rollover=rollover_env.lower() == "true",
            rollover_hour_utc=rollover_hour,
        )
