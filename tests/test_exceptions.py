"""Tests for custom exceptions."""

from todo_bot.exceptions import (
    ConfigurationError,
    StorageConnectionError,
    StorageError,
    StorageInitializationError,
    StorageOperationError,
    TaskNotFoundError,
    TodoBotError,
    ValidationError,
)


class TestTodoBotError:
    """Tests for TodoBotError base exception."""

    def test_base_exception(self) -> None:
        """Test TodoBotError is a valid exception.

        Verifies that TodoBotError can be instantiated with a message
        and properly inherits from the base Exception class.
        """
        error = TodoBotError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error(self) -> None:
        """Test ValidationError inherits from TodoBotError.

        Verifies that ValidationError correctly inherits from TodoBotError
        and can be instantiated with a validation message.
        """
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert isinstance(error, TodoBotError)


class TestTaskNotFoundError:
    """Tests for TaskNotFoundError exception."""

    def test_default_message(self) -> None:
        """Test TaskNotFoundError with default message.

        Verifies that when no custom message is provided, the exception
        generates a default message containing the task ID.
        """
        error = TaskNotFoundError(task_id=42)
        assert error.task_id == 42
        assert "Task #42 not found" in str(error)
        assert isinstance(error, TodoBotError)

    def test_custom_message(self) -> None:
        """Test TaskNotFoundError with custom message.

        Verifies that a custom message can be provided and will be used
        instead of the default generated message.
        """
        error = TaskNotFoundError(task_id=99, message="Custom error for task 99")
        assert error.task_id == 99
        assert str(error) == "Custom error for task 99"
        assert isinstance(error, TodoBotError)

    def test_none_message_uses_default(self) -> None:
        """Test TaskNotFoundError with None message uses default.

        Verifies that explicitly passing None as the message parameter
        results in the default message being used.
        """
        error = TaskNotFoundError(task_id=7, message=None)
        assert error.task_id == 7
        assert "Task #7 not found" in str(error)


class TestStorageError:
    """Tests for StorageError and its subclasses."""

    def test_storage_error(self) -> None:
        """Test StorageError inherits from TodoBotError.

        Verifies that StorageError can be instantiated with a message
        and properly inherits from TodoBotError.
        """
        error = StorageError("Storage failed")
        assert str(error) == "Storage failed"
        assert isinstance(error, TodoBotError)

    def test_storage_connection_error(self) -> None:
        """Test StorageConnectionError inherits from StorageError.

        Verifies the inheritance chain: StorageConnectionError inherits
        from StorageError, which in turn inherits from TodoBotError.
        """
        error = StorageConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, StorageError)
        assert isinstance(error, TodoBotError)

    def test_storage_initialization_error(self) -> None:
        """Test StorageInitializationError inherits from StorageError.

        Verifies the inheritance chain: StorageInitializationError inherits
        from StorageError, which in turn inherits from TodoBotError.
        """
        error = StorageInitializationError("Init failed")
        assert str(error) == "Init failed"
        assert isinstance(error, StorageError)
        assert isinstance(error, TodoBotError)

    def test_storage_operation_error(self) -> None:
        """Test StorageOperationError inherits from StorageError.

        Verifies the inheritance chain: StorageOperationError inherits
        from StorageError, which in turn inherits from TodoBotError.
        """
        error = StorageOperationError("Operation failed")
        assert str(error) == "Operation failed"
        assert isinstance(error, StorageError)
        assert isinstance(error, TodoBotError)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error(self) -> None:
        """Test ConfigurationError inherits from TodoBotError.

        Verifies that ConfigurationError can be instantiated with a message
        and properly inherits from TodoBotError.
        """
        error = ConfigurationError("Config missing")
        assert str(error) == "Config missing"
        assert isinstance(error, TodoBotError)
