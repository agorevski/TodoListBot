"""SQLite implementation of task storage with migration support."""

import asyncio
import functools
import logging
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import TypeVar

import aiosqlite

from ..config import (
    CONNECTION_RETRY_DELAY_SECONDS,
    DEFAULT_DB_PATH,
    MAX_CONNECTION_RETRIES,
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    SCHEMA_VERSION,
)
from ..exceptions import (
    StorageConnectionError,
    StorageInitializationError,
    StorageOperationError,
    ValidationError,
)
from ..models.task import Priority, Task
from .base import TaskStorage

logger = logging.getLogger(__name__)

# Type variable for retry decorator
T = TypeVar("T")


def with_retry(
    max_retries: int = MAX_CONNECTION_RETRIES,
    delay: float = CONNECTION_RETRY_DELAY_SECONDS,
    exceptions: tuple = (aiosqlite.Error,),
) -> Callable:
    """Decorator to retry async operations on transient failures.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "Operation %s failed (attempt %d/%d): %s. Retrying in %.1fs...",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            str(e),
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "Operation %s failed after %d attempts: %s",
                            func.__name__,
                            max_retries + 1,
                            str(e),
                        )
            raise StorageOperationError(
                f"Operation failed after {max_retries + 1} attempts: {last_exception}"
            ) from last_exception

        return wrapper

    return decorator


class SQLiteTaskStorage(TaskStorage):
    """SQLite-based storage implementation for tasks.

    This implementation uses aiosqlite for async database operations.
    Tasks are stored in a single table with all necessary fields.
    Includes schema versioning and migration support.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """Initialize the SQLite storage.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize the database and run migrations if needed.

        Raises:
            StorageInitializationError: If database initialization fails
        """
        try:
            # Ensure the directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row

            # Create schema version table if it doesn't exist
            await self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Get current schema version
            cursor = await self._connection.execute(
                "SELECT version FROM schema_version WHERE id = 1"
            )
            row = await cursor.fetchone()
            current_version = row["version"] if row else 0

            # Run migrations
            await self._run_migrations(current_version)

            await self._connection.commit()
            logger.info(
                "Database initialized at version %d (path: %s)",
                SCHEMA_VERSION,
                self.db_path,
            )
        except aiosqlite.Error as e:
            raise StorageInitializationError(
                f"Failed to initialize database: {e}"
            ) from e

    async def _run_migrations(self, current_version: int) -> None:
        """Run database migrations from current version to latest.

        Args:
            current_version: The current schema version
        """
        conn = self._ensure_connected()

        if current_version < 1:
            logger.info("Running migration to version 1...")
            # Create the tasks table (version 1 schema)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK(priority IN ('A', 'B', 'C')),
                    done INTEGER NOT NULL DEFAULT 0,
                    task_date TEXT NOT NULL,
                    server_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for common queries
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_user_channel_date
                ON tasks(server_id, channel_id, user_id, task_date)
            """
            )

            # Create index for cleanup operations
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_date
                ON tasks(task_date)
            """
            )

            logger.info("Migration to version 1 complete")

        if current_version < 2:
            logger.info("Running migration to version 2...")
            # Add composite index for queries that filter by done status
            # This improves performance for get_tasks with include_done=False
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tasks_user_done
                ON tasks(server_id, channel_id, user_id, task_date, done)
            """
            )
            logger.info("Migration to version 2 complete")

        # Update schema version
        await conn.execute(
            """
            INSERT OR REPLACE INTO schema_version (id, version, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
        """,
            (SCHEMA_VERSION,),
        )

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.debug("Database connection closed")

    def _ensure_connected(self) -> aiosqlite.Connection:
        """Ensure the database connection is active.

        Returns:
            The active database connection

        Raises:
            StorageConnectionError: If the database is not initialized
        """
        if self._connection is None:
            raise StorageConnectionError(
                "Database not initialized. Call initialize() first."
            )
        return self._connection

    def _row_to_task(self, row: aiosqlite.Row) -> Task:
        """Convert a database row to a Task object.

        Args:
            row: Database row

        Returns:
            Task object
        """
        return Task(
            id=row["id"],
            description=row["description"],
            priority=Priority.from_string(row["priority"]),
            done=bool(row["done"]),
            task_date=date.fromisoformat(row["task_date"]),
            server_id=row["server_id"],
            channel_id=row["channel_id"],
            user_id=row["user_id"],
        )

    def _validate_description(self, description: str) -> str:
        """Validate and sanitize a task description.

        This provides defense-in-depth validation at the storage layer,
        ensuring data integrity even if called from non-cog entry points.

        Args:
            description: The task description to validate

        Returns:
            The validated description (stripped of whitespace)

        Raises:
            ValidationError: If the description is invalid
        """
        if not description or not isinstance(description, str):
            raise ValidationError("Task description is required.")

        stripped = description.strip()

        if len(stripped) < MIN_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"Task description must be at least {MIN_DESCRIPTION_LENGTH} character(s)."
            )

        if len(stripped) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"Task description too long ({len(stripped)} chars). "
                f"Maximum is {MAX_DESCRIPTION_LENGTH} characters."
            )

        return stripped

    @with_retry()
    async def add_task(
        self,
        description: str,
        priority: Priority,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date | None = None,
    ) -> Task:
        """Add a new task to the database.

        Args:
            description: Task description (validated for length)
            priority: Task priority (A, B, or C)
            server_id: Discord server (guild) ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            task_date: Optional date for the task (defaults to today)

        Returns:
            The created Task with its assigned ID

        Raises:
            ValidationError: If the description is invalid
            StorageOperationError: If the database operation fails
        """
        # Validate description at storage layer for defense in depth
        validated_description = self._validate_description(description)

        conn = self._ensure_connected()
        task_date = task_date or date.today()

        try:
            cursor = await conn.execute(
                """
                INSERT INTO tasks
                    (description, priority, task_date, server_id, channel_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    validated_description,
                    priority.value,
                    task_date.isoformat(),
                    server_id,
                    channel_id,
                    user_id,
                ),
            )
            await conn.commit()

            task_id = cursor.lastrowid
            if task_id is None:  # pragma: no cover
                raise StorageOperationError("Failed to get task ID after insert")

            logger.debug("Task #%d created for user %d", task_id, user_id)

            return Task(
                id=task_id,
                description=validated_description,
                priority=priority,
                done=False,
                task_date=task_date,
                server_id=server_id,
                channel_id=channel_id,
                user_id=user_id,
            )
        except aiosqlite.Error as e:
            raise StorageOperationError(f"Failed to add task: {e}") from e

    @with_retry()
    async def get_tasks(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date | None = None,
        include_done: bool = True,
    ) -> list[Task]:
        """Get tasks for a specific user in a channel."""
        conn = self._ensure_connected()
        task_date = task_date or date.today()

        query = """
            SELECT * FROM tasks
            WHERE server_id = ? AND channel_id = ? AND user_id = ?
                AND task_date = ?
        """
        params: list = [server_id, channel_id, user_id, task_date.isoformat()]

        if not include_done:
            query += " AND done = 0"

        # Order by priority (A first), then by done status, then by ID
        query += " ORDER BY priority ASC, done ASC, id ASC"

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

        return [self._row_to_task(row) for row in rows]

    @with_retry()
    async def get_task_by_id(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> Task | None:
        """Get a specific task by its ID."""
        conn = self._ensure_connected()

        cursor = await conn.execute(
            """
            SELECT * FROM tasks
            WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
            """,
            (task_id, server_id, channel_id, user_id),
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_task(row)

    @with_retry()
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
            description: New description (optional, validated for length)
            priority: New priority (optional)

        Returns:
            True if the task was found and updated, False otherwise

        Raises:
            ValidationError: If the description is invalid
        """
        if description is None and priority is None:
            return False  # Nothing to update

        # Validate description at storage layer for defense in depth
        validated_description = None
        if description is not None:
            validated_description = self._validate_description(description)

        conn = self._ensure_connected()

        # Use explicit query variants to avoid dynamic SQL construction
        if validated_description is not None and priority is not None:
            cursor = await conn.execute(
                """
                UPDATE tasks
                SET description = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
                """,
                (validated_description, priority.value, task_id, server_id, channel_id, user_id),
            )
        elif validated_description is not None:
            cursor = await conn.execute(
                """
                UPDATE tasks
                SET description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
                """,
                (validated_description, task_id, server_id, channel_id, user_id),
            )
        else:  # priority is not None
            cursor = await conn.execute(
                """
                UPDATE tasks
                SET priority = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
                """,
                (priority.value, task_id, server_id, channel_id, user_id),
            )

        await conn.commit()

        if cursor.rowcount > 0:
            logger.debug("Task #%d updated by user %d", task_id, user_id)
            return True
        return False

    @with_retry()
    async def mark_task_done(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> bool:
        """Mark a task as completed."""
        conn = self._ensure_connected()

        cursor = await conn.execute(
            """
            UPDATE tasks SET done = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
            """,
            (task_id, server_id, channel_id, user_id),
        )
        await conn.commit()

        return cursor.rowcount > 0

    @with_retry()
    async def mark_task_undone(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> bool:
        """Mark a task as not completed."""
        conn = self._ensure_connected()

        cursor = await conn.execute(
            """
            UPDATE tasks SET done = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
            """,
            (task_id, server_id, channel_id, user_id),
        )
        await conn.commit()

        return cursor.rowcount > 0

    @with_retry()
    async def clear_completed_tasks(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: date | None = None,
    ) -> int:
        """Remove all completed tasks for a user."""
        conn = self._ensure_connected()
        task_date = task_date or date.today()

        cursor = await conn.execute(
            """
            DELETE FROM tasks
            WHERE server_id = ? AND channel_id = ? AND user_id = ?
                AND task_date = ? AND done = 1
            """,
            (server_id, channel_id, user_id, task_date.isoformat()),
        )
        await conn.commit()

        return cursor.rowcount

    @with_retry()
    async def delete_task(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> bool:
        """Delete a specific task."""
        conn = self._ensure_connected()

        cursor = await conn.execute(
            """
            DELETE FROM tasks
            WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
            """,
            (task_id, server_id, channel_id, user_id),
        )
        await conn.commit()

        return cursor.rowcount > 0

    @with_retry()
    async def cleanup_old_tasks(self, retention_days: int) -> int:
        """Remove tasks older than the specified retention period.

        Args:
            retention_days: Number of days to retain tasks (must be > 0)

        Returns:
            The number of tasks that were removed
        """
        if retention_days <= 0:
            return 0

        conn = self._ensure_connected()
        cutoff_date = date.today() - timedelta(days=retention_days)

        cursor = await conn.execute(
            """
            DELETE FROM tasks
            WHERE task_date < ?
            """,
            (cutoff_date.isoformat(),),
        )
        await conn.commit()

        count = cursor.rowcount
        if count > 0:
            logger.info(
                "Cleaned up %d tasks older than %d days (before %s)",
                count,
                retention_days,
                cutoff_date,
            )

        return count

    @with_retry()
    async def get_stats(self) -> dict:
        """Get database statistics for health checks.

        Returns:
            Dictionary with database statistics
        """
        conn = self._ensure_connected()

        # Get total task count
        cursor = await conn.execute("SELECT COUNT(*) as count FROM tasks")
        row = await cursor.fetchone()
        total_tasks = row["count"] if row else 0

        # Get unique users count
        cursor = await conn.execute(
            "SELECT COUNT(DISTINCT user_id) as count FROM tasks"
        )
        row = await cursor.fetchone()
        unique_users = row["count"] if row else 0

        # Get schema version
        cursor = await conn.execute("SELECT version FROM schema_version WHERE id = 1")
        row = await cursor.fetchone()
        schema_version = row["version"] if row else 0

        return {
            "total_tasks": total_tasks,
            "unique_users": unique_users,
            "schema_version": schema_version,
            "database_path": self.db_path,
        }

    @with_retry()
    async def rollover_incomplete_tasks(
        self,
        from_date: date,
        to_date: date,
    ) -> int:
        """Copy incomplete tasks from one date to the next day.

        This method finds all incomplete (not done) tasks for the from_date
        and creates copies of them for the to_date. The original tasks
        remain unchanged on their original date.

        Tasks are only rolled over if an identical task (same description,
        priority, server, channel, user) does not already exist on the to_date.

        Args:
            from_date: The source date to copy incomplete tasks from
            to_date: The target date to copy tasks to

        Returns:
            The number of tasks that were rolled over
        """
        conn = self._ensure_connected()

        # Get all incomplete tasks from the source date
        cursor = await conn.execute(
            """
            SELECT description, priority, server_id, channel_id, user_id
            FROM tasks
            WHERE task_date = ? AND done = 0
            """,
            (from_date.isoformat(),),
        )
        incomplete_tasks = await cursor.fetchall()

        if not incomplete_tasks:
            return 0

        # Batch fetch: Get all existing tasks on the target date in a single query
        # This eliminates the N+1 query problem
        cursor = await conn.execute(
            """
            SELECT description, priority, server_id, channel_id, user_id
            FROM tasks
            WHERE task_date = ?
            """,
            (to_date.isoformat(),),
        )
        existing_tasks = await cursor.fetchall()

        # Build a set of existing task signatures for O(1) lookup
        existing_signatures: set[tuple[str, str, int, int, int]] = {
            (
                row["description"],
                row["priority"],
                row["server_id"],
                row["channel_id"],
                row["user_id"],
            )
            for row in existing_tasks
        }

        rolled_over_count = 0

        for task_row in incomplete_tasks:
            description = task_row["description"]
            priority = task_row["priority"]
            server_id = task_row["server_id"]
            channel_id = task_row["channel_id"]
            user_id = task_row["user_id"]

            # Check if an identical task already exists using set membership
            task_signature = (description, priority, server_id, channel_id, user_id)
            if task_signature in existing_signatures:
                # Skip this task - already exists on target date
                continue

            # Create a copy of the task for the new date
            await conn.execute(
                """
                INSERT INTO tasks
                    (description, priority, task_date, server_id, channel_id, user_id, done)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    description,
                    priority,
                    to_date.isoformat(),
                    server_id,
                    channel_id,
                    user_id,
                ),
            )
            rolled_over_count += 1

        await conn.commit()

        if rolled_over_count > 0:
            logger.info(
                "Rolled over %d incomplete tasks from %s to %s",
                rolled_over_count,
                from_date,
                to_date,
            )

        return rolled_over_count

    @with_retry()
    async def get_all_user_contexts(
        self,
        task_date: date,
    ) -> list[tuple[int, int, int]]:
        """Get all unique (server_id, channel_id, user_id) combinations for a date.

        This is used by the scheduler to determine which users have tasks
        that may need to be rolled over.

        Args:
            task_date: The date to get user contexts for

        Returns:
            List of (server_id, channel_id, user_id) tuples
        """
        conn = self._ensure_connected()

        cursor = await conn.execute(
            """
            SELECT DISTINCT server_id, channel_id, user_id
            FROM tasks
            WHERE task_date = ?
            """,
            (task_date.isoformat(),),
        )
        rows = await cursor.fetchall()

        return [(row["server_id"], row["channel_id"], row["user_id"]) for row in rows]
