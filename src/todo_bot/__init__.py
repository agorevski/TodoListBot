"""Discord A/B/C Todo Bot - A task management bot using the A/B/C priority system."""

from .bot import TodoBot, create_bot, run_bot, setup_logging
from .config import (
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    RATE_LIMIT_COMMANDS,
    RATE_LIMIT_SECONDS,
    VIEW_TIMEOUT_SECONDS,
    MAX_BUTTONS_PER_VIEW,
    BUTTONS_PER_ROW,
    DEFAULT_DB_PATH,
    SCHEMA_VERSION,
    BotConfig,
)
from .exceptions import (
    TodoBotError,
    ValidationError,
    TaskNotFoundError,
    StorageError,
    StorageConnectionError,
    StorageInitializationError,
    StorageOperationError,
    ConfigurationError,
)

__all__ = [
    # Bot
    "TodoBot",
    "create_bot",
    "run_bot",
    "setup_logging",
    # Config
    "MAX_DESCRIPTION_LENGTH",
    "MIN_DESCRIPTION_LENGTH",
    "RATE_LIMIT_COMMANDS",
    "RATE_LIMIT_SECONDS",
    "VIEW_TIMEOUT_SECONDS",
    "MAX_BUTTONS_PER_VIEW",
    "BUTTONS_PER_ROW",
    "DEFAULT_DB_PATH",
    "SCHEMA_VERSION",
    "BotConfig",
    # Exceptions
    "TodoBotError",
    "ValidationError",
    "TaskNotFoundError",
    "StorageError",
    "StorageConnectionError",
    "StorageInitializationError",
    "StorageOperationError",
    "ConfigurationError",
]

__version__ = "1.0.0"
