"""Discord A/B/C Todo Bot - A task management bot using the A/B/C priority system."""

from .bot import TodoBot, create_bot, run_bot, setup_logging
from .config import (
    BUTTONS_PER_ROW,
    CONNECTION_RETRY_DELAY_SECONDS,
    DEFAULT_DB_PATH,
    DEFAULT_RETENTION_DAYS,
    MAX_BUTTONS_PER_VIEW,
    MAX_CONNECTION_RETRIES,
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    RATE_LIMIT_COMMANDS,
    RATE_LIMIT_SECONDS,
    SCHEMA_VERSION,
    VIEW_TIMEOUT_SECONDS,
    BotConfig,
)
from .exceptions import (
    ConfigurationError,
    StorageConnectionError,
    StorageError,
    StorageInitializationError,
    StorageOperationError,
    TaskNotFoundError,
    TodoBotError,
    ValidationError,
)
from .health import (
    check_database_accessible,
    check_imports,
    run_health_check,
)
from .messages import (
    DisplayMessages,
    ErrorMessages,
    LogMessages,
    SuccessMessages,
)
from .validators import (
    sanitize_description,
    validate_date_string,
    validate_description,
    validate_priority,
    validate_retention_days,
    validate_task_id,
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
    "MAX_CONNECTION_RETRIES",
    "CONNECTION_RETRY_DELAY_SECONDS",
    "DEFAULT_RETENTION_DAYS",
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
    # Validators
    "sanitize_description",
    "validate_description",
    "validate_priority",
    "validate_task_id",
    "validate_date_string",
    "validate_retention_days",
    # Messages
    "ErrorMessages",
    "SuccessMessages",
    "DisplayMessages",
    "LogMessages",
    # Health
    "check_database_accessible",
    "check_imports",
    "run_health_check",
]

__version__ = "1.0.0"
