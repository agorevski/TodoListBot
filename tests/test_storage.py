"""Tests for the SQLite storage implementation."""

from datetime import date, timedelta

import pytest

from tests.conftest import TEST_CHANNEL_ID, TEST_SERVER_ID, TEST_USER_ID
from todo_bot.exceptions import StorageConnectionError
from todo_bot.models.task import Priority
from todo_bot.storage.sqlite import SQLiteTaskStorage


class TestSQLiteTaskStorage:
    """Tests for SQLiteTaskStorage class."""

    @pytest.mark.asyncio
    async def test_add_task(self, storage: SQLiteTaskStorage) -> None:
        """Test adding a new task."""
        task = await storage.add_task(
            description="Test task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert task.id is not None
        assert task.description == "Test task"
        assert task.priority == Priority.A
        assert task.done is False
        assert task.task_date == date.today()

    @pytest.mark.asyncio
    async def test_add_task_with_custom_date(self, storage: SQLiteTaskStorage) -> None:
        """Test adding a task with a custom date."""
        custom_date = date(2024, 12, 25)
        task = await storage.add_task(
            description="Christmas task",
            priority=Priority.B,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=custom_date,
        )

        assert task.task_date == custom_date

    @pytest.mark.asyncio
    async def test_get_tasks_empty(self, storage: SQLiteTaskStorage) -> None:
        """Test getting tasks when none exist."""
        tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert tasks == []

    @pytest.mark.asyncio
    async def test_get_tasks(self, storage: SQLiteTaskStorage) -> None:
        """Test getting tasks for a user."""
        # Add some tasks
        await storage.add_task(
            description="Task 1",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        await storage.add_task(
            description="Task 2",
            priority=Priority.B,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert len(tasks) == 2
        # Tasks should be ordered by priority (A first)
        assert tasks[0].priority == Priority.A
        assert tasks[1].priority == Priority.B

    @pytest.mark.asyncio
    async def test_get_tasks_filtered_by_date(self, storage: SQLiteTaskStorage) -> None:
        """Test that tasks are filtered by date."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        await storage.add_task(
            description="Today's task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=today,
        )
        await storage.add_task(
            description="Yesterday's task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=yesterday,
        )

        # Get today's tasks
        today_tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=today,
        )
        assert len(today_tasks) == 1
        assert today_tasks[0].description == "Today's task"

        # Get yesterday's tasks
        yesterday_tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=yesterday,
        )
        assert len(yesterday_tasks) == 1
        assert yesterday_tasks[0].description == "Yesterday's task"

    @pytest.mark.asyncio
    async def test_get_tasks_exclude_done(self, storage: SQLiteTaskStorage) -> None:
        """Test excluding completed tasks."""
        task = await storage.add_task(
            description="Task to complete",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        await storage.add_task(
            description="Incomplete task",
            priority=Priority.B,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        await storage.mark_task_done(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        # Include done tasks
        all_tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            include_done=True,
        )
        assert len(all_tasks) == 2

        # Exclude done tasks
        incomplete_tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            include_done=False,
        )
        assert len(incomplete_tasks) == 1
        assert incomplete_tasks[0].description == "Incomplete task"

    @pytest.mark.asyncio
    async def test_get_tasks_different_users(self, storage: SQLiteTaskStorage) -> None:
        """Test that tasks are scoped by user."""
        user1_id = 111
        user2_id = 222

        await storage.add_task(
            description="User 1 task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=user1_id,
        )
        await storage.add_task(
            description="User 2 task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=user2_id,
        )

        user1_tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=user1_id,
        )
        assert len(user1_tasks) == 1
        assert user1_tasks[0].description == "User 1 task"

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, storage: SQLiteTaskStorage) -> None:
        """Test getting a specific task by ID."""
        task = await storage.add_task(
            description="Test task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        retrieved = await storage.get_task_by_id(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.description == "Test task"

    @pytest.mark.asyncio
    async def test_get_task_by_id_not_found(self, storage: SQLiteTaskStorage) -> None:
        """Test getting a task that doesn't exist."""
        retrieved = await storage.get_task_by_id(
            task_id=99999,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_task_by_id_wrong_user(self, storage: SQLiteTaskStorage) -> None:
        """Test that task lookup is scoped by user."""
        task = await storage.add_task(
            description="Test task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        # Try to get with different user ID
        retrieved = await storage.get_task_by_id(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=999999,  # Different user
        )

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_mark_task_done(self, storage: SQLiteTaskStorage) -> None:
        """Test marking a task as done."""
        task = await storage.add_task(
            description="Test task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        success = await storage.mark_task_done(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert success is True

        # Verify task is marked done
        retrieved = await storage.get_task_by_id(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        assert retrieved is not None
        assert retrieved.done is True

    @pytest.mark.asyncio
    async def test_mark_task_done_not_found(self, storage: SQLiteTaskStorage) -> None:
        """Test marking a non-existent task as done."""
        success = await storage.mark_task_done(
            task_id=99999,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_mark_task_undone(self, storage: SQLiteTaskStorage) -> None:
        """Test marking a task as undone."""
        task = await storage.add_task(
            description="Test task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        await storage.mark_task_done(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        success = await storage.mark_task_undone(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert success is True

        # Verify task is marked undone
        retrieved = await storage.get_task_by_id(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        assert retrieved is not None
        assert retrieved.done is False

    @pytest.mark.asyncio
    async def test_mark_task_undone_not_found(self, storage: SQLiteTaskStorage) -> None:
        """Test marking a non-existent task as undone."""
        success = await storage.mark_task_undone(
            task_id=99999,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_clear_completed_tasks(self, storage: SQLiteTaskStorage) -> None:
        """Test clearing completed tasks."""
        task1 = await storage.add_task(
            description="Task 1",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        task2 = await storage.add_task(
            description="Task 2",
            priority=Priority.B,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        await storage.add_task(
            description="Task 3",
            priority=Priority.C,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        # Mark two tasks as done
        await storage.mark_task_done(
            task_id=task1.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        await storage.mark_task_done(
            task_id=task2.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        # Clear completed tasks
        count = await storage.clear_completed_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert count == 2

        # Verify only incomplete task remains
        tasks = await storage.get_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        assert len(tasks) == 1
        assert tasks[0].description == "Task 3"

    @pytest.mark.asyncio
    async def test_clear_completed_tasks_empty(
        self, storage: SQLiteTaskStorage
    ) -> None:
        """Test clearing when no completed tasks exist."""
        await storage.add_task(
            description="Incomplete task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        count = await storage.clear_completed_tasks(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_task(self, storage: SQLiteTaskStorage) -> None:
        """Test deleting a task."""
        task = await storage.add_task(
            description="Test task",
            priority=Priority.A,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        success = await storage.delete_task(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert success is True

        # Verify task is deleted
        retrieved = await storage.get_task_by_id(
            task_id=task.id,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, storage: SQLiteTaskStorage) -> None:
        """Test deleting a non-existent task."""
        success = await storage.delete_task(
            task_id=99999,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_ensure_connected_raises_without_init(self) -> None:
        """Test that operations fail if storage is not initialized."""
        storage = SQLiteTaskStorage(db_path="nonexistent.db")

        with pytest.raises(StorageConnectionError, match="not initialized"):
            storage._ensure_connected()

    @pytest.mark.asyncio
    async def test_close_without_connection(self) -> None:
        """Test that close works even without a connection."""
        storage = SQLiteTaskStorage(db_path="nonexistent.db")
        await storage.close()  # Should not raise


class TestTaskStorageContextManager:
    """Tests for TaskStorage async context manager protocol."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, tmp_path) -> None:
        """Test async context manager initializes and closes storage."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteTaskStorage(db_path=db_path)

        async with storage:
            # Verify storage is initialized
            assert storage._connection is not None
            # Can perform operations
            stats = await storage.get_stats()
            assert "schema_version" in stats

        # Verify storage is closed after exiting
        assert storage._connection is None

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self, tmp_path) -> None:
        """Test context manager closes storage even on exception."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteTaskStorage(db_path=db_path)

        with pytest.raises(ValueError):
            async with storage:
                assert storage._connection is not None
                raise ValueError("Test exception")

        # Verify storage is closed after exception
        assert storage._connection is None
