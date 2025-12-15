"""Abstract base class for task storage implementations."""

from abc import ABC, abstractmethod
from datetime import date
from types import TracebackType

from ..models.task import Priority, Task


class TaskStorage(ABC):
    """Abstract base class defining the interface for task storage.

    This interface allows for easy swapping of storage backends
    (e.g., SQLite, PostgreSQL, MongoDB) without changing the rest of the code.

    Supports async context manager protocol for proper resource management:
        async with storage:
            await storage.add_task(...)
    """

    async def __aenter__(self) -> "TaskStorage":
        """Enter the async context manager.

        Returns:
            Self after initialization
        """
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        await self.close()

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend.

        This method should be called before any other operations.
        It should set up any necessary database connections, tables, etc.

        Raises:
            StorageInitializationError: If initialization fails
        """
        ...  # pragma: no cover

    @abstractmethod
    async def close(self) -> None:
        """Close the storage backend and release any resources."""
        ...  # pragma: no cover

    @abstractmethod
    async def add_task(
        self,
        description: str,
        priority: Priority,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date | None = None,
    ) -> Task:
        """Add a new task to storage.

        Args:
            description: Task description text
            priority: Task priority (A, B, or C)
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            task_date: Optional date for the task (defaults to today)

        Returns:
            The created Task with its assigned ID

        Raises:
            StorageOperationError: If the operation fails
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get_tasks(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date | None = None,
        include_done: bool = True,
    ) -> list[Task]:
        """Get tasks for a specific user in a channel.

        Args:
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            task_date: Optional date to filter by (defaults to today)
            include_done: Whether to include completed tasks

        Returns:
            List of tasks matching the criteria
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get_task_by_id(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> Task | None:
        """Get a specific task by its ID.

        Args:
            task_id: The task ID
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID

        Returns:
            The task if found, None otherwise
        """
        ...  # pragma: no cover

    @abstractmethod
    async def update_task(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
        description: str | None = None,
        priority: Priority | None = None,
    ) -> bool:
        """Update a task's description and/or priority.

        Args:
            task_id: The task ID
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            description: New description (optional)
            priority: New priority (optional)

        Returns:
            True if the task was found and updated, False otherwise
        """
        ...  # pragma: no cover

    @abstractmethod
    async def mark_task_done(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> bool:
        """Mark a task as completed.

        Args:
            task_id: The task ID
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID

        Returns:
            True if the task was found and updated, False otherwise
        """
        ...  # pragma: no cover

    @abstractmethod
    async def mark_task_undone(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> bool:
        """Mark a task as not completed.

        Args:
            task_id: The task ID
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID

        Returns:
            True if the task was found and updated, False otherwise
        """
        ...  # pragma: no cover

    @abstractmethod
    async def clear_completed_tasks(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date | None = None,
    ) -> int:
        """Remove all completed tasks for a user.

        Args:
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            task_date: Optional date to filter by (defaults to today)

        Returns:
            The number of tasks that were removed
        """
        ...  # pragma: no cover

    @abstractmethod
    async def delete_task(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> bool:
        """Delete a specific task.

        Args:
            task_id: The task ID
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID

        Returns:
            True if the task was found and deleted, False otherwise
        """
        ...  # pragma: no cover

    @abstractmethod
    async def cleanup_old_tasks(self, retention_days: int) -> int:
        """Remove tasks older than the specified retention period.

        Args:
            retention_days: Number of days to retain tasks (must be > 0)

        Returns:
            The number of tasks that were removed
        """
        ...  # pragma: no cover

    @abstractmethod
    async def get_stats(self) -> dict:
        """Get storage statistics for health checks.

        Returns:
            Dictionary with storage statistics
        """
        ...  # pragma: no cover
