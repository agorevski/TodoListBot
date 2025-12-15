"""Custom exceptions for the Discord A/B/C Todo Bot."""


class TodoBotError(Exception):
    """Base exception for all Todo Bot errors."""

    pass


class ValidationError(TodoBotError):
    """Raised when input validation fails."""

    pass


class TaskNotFoundError(TodoBotError):
    """Raised when a task cannot be found."""

    def __init__(self, task_id: int, message: str = None) -> None:
        """Initialize the exception.

        Args:
            task_id: The task ID that was not found
            message: Optional custom message
        """
        self.task_id = task_id
        if message is None:
            message = f"Task #{task_id} not found"
        super().__init__(message)


class StorageError(TodoBotError):
    """Base exception for storage-related errors."""

    pass


class StorageConnectionError(StorageError):
    """Raised when storage connection fails."""

    pass


class StorageInitializationError(StorageError):
    """Raised when storage initialization fails."""

    pass


class StorageOperationError(StorageError):
    """Raised when a storage operation fails."""

    pass


class ConfigurationError(TodoBotError):
    """Raised when configuration is invalid or missing."""

    pass
