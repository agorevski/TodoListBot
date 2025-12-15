"""SQLite implementation of task storage with migration support."""

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

import aiosqlite

from .base import TaskStorage
from ..config import (
    DEFAULT_DB_PATH,
    SCHEMA_VERSION,
)
from ..exceptions import (
    StorageConnectionError,
    StorageInitializationError,
    StorageOperationError,
)
from ..models.task import Task, Priority

logger = logging.getLogger(__name__)

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
        self._connection: Optional[aiosqlite.Connection] = None

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
            await self._connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

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
            await conn.execute("""
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
            """)

            # Create indexes for common queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_channel_date
                ON tasks(server_id, channel_id, user_id, task_date)
            """)

            # Create index for cleanup operations
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_date
                ON tasks(task_date)
            """)

            logger.info("Migration to version 1 complete")

        # Future migrations would go here:
        # if current_version < 2:
        #     logger.info("Running migration to version 2...")
        #     # Add new columns, tables, etc.
        #     logger.info("Migration to version 2 complete")

        # Update schema version
        await conn.execute("""
            INSERT OR REPLACE INTO schema_version (id, version, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
        """, (SCHEMA_VERSION,))

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

    async def add_task(
        self,
        description: str,
        priority: Priority,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: Optional[date] = None,
    ) -> Task:
        """Add a new task to the database."""
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
                    description,
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
                description=description,
                priority=priority,
                done=False,
                task_date=task_date,
                server_id=server_id,
                channel_id=channel_id,
                user_id=user_id,
            )
        except aiosqlite.Error as e:
            raise StorageOperationError(f"Failed to add task: {e}") from e

    async def get_tasks(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: Optional[date] = None,
        include_done: bool = True,
    ) -> List[Task]:
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

    async def get_task_by_id(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
    ) -> Optional[Task]:
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

    async def update_task(
        self,
        task_id: int,
        server_id: int,
        channel_id: int,
        user_id: int,
        description: Optional[str] = None,
        priority: Optional[Priority] = None,
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
        if description is None and priority is None:
            return False  # Nothing to update

        conn = self._ensure_connected()

        # Build dynamic UPDATE query using explicit column updates
        set_clauses = []
        params: list = []

        if description is not None:
            set_clauses.append("description = ?")
            params.append(description)

        if priority is not None:
            set_clauses.append("priority = ?")
            params.append(priority.value)

        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([task_id, server_id, channel_id, user_id])

        query = f"""
            UPDATE tasks SET {', '.join(set_clauses)}
            WHERE id = ? AND server_id = ? AND channel_id = ? AND user_id = ?
        """

        cursor = await conn.execute(query, params)
        await conn.commit()

        if cursor.rowcount > 0:
            logger.debug("Task #%d updated by user %d", task_id, user_id)
            return True
        return False

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

    async def clear_completed_tasks(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        task_date: Optional[date] = None,
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
        cursor = await conn.execute(
            "SELECT version FROM schema_version WHERE id = 1"
        )
        row = await cursor.fetchone()
        schema_version = row["version"] if row else 0

        return {
            "total_tasks": total_tasks,
            "unique_users": unique_users,
            "schema_version": schema_version,
            "database_path": self.db_path,
        }
