"""Tests for the rollover functionality in storage."""

from datetime import date, timedelta

import pytest

from todo_bot.models.task import Priority
from todo_bot.storage.sqlite import SQLiteTaskStorage

class TestRolloverIncompleteTasks:
    """Tests for the rollover_incomplete_tasks storage method."""

    @pytest.fixture
    async def storage(self, tmp_path) -> SQLiteTaskStorage:
        """Create an initialized SQLite storage for testing.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.

        Yields:
            SQLiteTaskStorage: An initialized storage instance for testing.
        """
        db_path = str(tmp_path / "test_rollover.db")
        storage = SQLiteTaskStorage(db_path=db_path)
        await storage.initialize()
        yield storage
        await storage.close()

    @pytest.mark.asyncio
    async def test_rollover_no_tasks(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover returns 0 when there are no tasks to roll over.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        count = await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        assert count == 0

    @pytest.mark.asyncio
    async def test_rollover_all_tasks_complete(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover returns 0 when all tasks are completed.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        # Add a completed task from yesterday
        task = await storage.add_task(
            description="Completed task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        await storage.mark_task_done(
            task_id=task.id,
            server_id=123,
            channel_id=456,
            user_id=789,
        )
        
        count = await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        assert count == 0

    @pytest.mark.asyncio
    async def test_rollover_incomplete_tasks(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover copies incomplete tasks to the new date.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        # Add incomplete tasks from yesterday
        await storage.add_task(
            description="Incomplete task 1",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        await storage.add_task(
            description="Incomplete task 2",
            priority=Priority.B,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        
        count = await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        assert count == 2
        
        # Verify tasks exist on both dates
        yesterday_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        today_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        
        assert len(yesterday_tasks) == 2
        assert len(today_tasks) == 2
        
        # Verify today's tasks have the same descriptions
        today_descriptions = {t.description for t in today_tasks}
        assert "Incomplete task 1" in today_descriptions
        assert "Incomplete task 2" in today_descriptions

    @pytest.mark.asyncio
    async def test_rollover_preserves_priority(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover preserves the original task's priority.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        await storage.add_task(
            description="Priority A task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        await storage.add_task(
            description="Priority C task",
            priority=Priority.C,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        
        await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        today_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        
        priorities = {t.description: t.priority for t in today_tasks}
        assert priorities["Priority A task"] == Priority.A
        assert priorities["Priority C task"] == Priority.C

    @pytest.mark.asyncio
    async def test_rollover_creates_undone_tasks(self, storage: SQLiteTaskStorage) -> None:
        """Verify rolled over tasks are marked as not done.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        await storage.add_task(
            description="Task to rollover",
            priority=Priority.B,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        
        await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        today_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        
        assert len(today_tasks) == 1
        assert today_tasks[0].done is False

    @pytest.mark.asyncio
    async def test_rollover_skips_duplicates(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover does not create duplicate tasks on the target date.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        # Add incomplete task from yesterday
        await storage.add_task(
            description="Same task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        
        # Add the same task for today already
        await storage.add_task(
            description="Same task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        
        count = await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        # Should not create a duplicate
        assert count == 0
        
        today_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        assert len(today_tasks) == 1

    @pytest.mark.asyncio
    async def test_rollover_mixed_complete_incomplete(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover only rolls over incomplete tasks, not completed ones.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        # Add incomplete task
        await storage.add_task(
            description="Incomplete",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        
        # Add completed task
        completed = await storage.add_task(
            description="Completed",
            priority=Priority.B,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        await storage.mark_task_done(
            task_id=completed.id,
            server_id=123,
            channel_id=456,
            user_id=789,
        )
        
        count = await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        assert count == 1
        
        today_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        assert len(today_tasks) == 1
        assert today_tasks[0].description == "Incomplete"

    @pytest.mark.asyncio
    async def test_rollover_multiple_users(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover handles tasks for multiple users independently.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        # User 1's task
        await storage.add_task(
            description="User 1 task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=111,
            task_date=yesterday,
        )
        
        # User 2's task
        await storage.add_task(
            description="User 2 task",
            priority=Priority.B,
            server_id=123,
            channel_id=456,
            user_id=222,
            task_date=yesterday,
        )
        
        count = await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        assert count == 2
        
        # Verify each user has their own task
        user1_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=111,
            task_date=today,
        )
        user2_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=222,
            task_date=today,
        )
        
        assert len(user1_tasks) == 1
        assert user1_tasks[0].description == "User 1 task"
        assert len(user2_tasks) == 1
        assert user2_tasks[0].description == "User 2 task"

    @pytest.mark.asyncio
    async def test_rollover_original_tasks_unchanged(self, storage: SQLiteTaskStorage) -> None:
        """Verify original tasks remain unchanged on the old date after rollover.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        original = await storage.add_task(
            description="Original task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        
        await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        # Verify original task is unchanged
        yesterday_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=yesterday,
        )
        
        assert len(yesterday_tasks) == 1
        assert yesterday_tasks[0].id == original.id
        assert yesterday_tasks[0].description == "Original task"
        assert yesterday_tasks[0].task_date == yesterday

    @pytest.mark.asyncio
    async def test_rollover_batch_query_efficiency(self, storage: SQLiteTaskStorage) -> None:
        """Verify rollover correctly handles multiple tasks efficiently.

        This test verifies the batch query optimization by creating many
        incomplete tasks and checking that rollover works correctly when
        some already exist on the target date.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        # Create 10 incomplete tasks from yesterday
        for i in range(10):
            await storage.add_task(
                description=f"Task {i}",
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
                task_date=yesterday,
            )
        
        # Pre-create 5 of them on today (simulate partial rollover)
        for i in range(5):
            await storage.add_task(
                description=f"Task {i}",
                priority=Priority.A,
                server_id=123,
                channel_id=456,
                user_id=789,
                task_date=today,
            )
        
        # Rollover should only create 5 new tasks (the ones not already on today)
        count = await storage.rollover_incomplete_tasks(
            from_date=yesterday,
            to_date=today,
        )
        
        assert count == 5
        
        # Verify all 10 tasks now exist on today
        today_tasks = await storage.get_tasks(
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        assert len(today_tasks) == 10
        
        # Verify all descriptions are present
        descriptions = {t.description for t in today_tasks}
        for i in range(10):
            assert f"Task {i}" in descriptions


class TestGetAllUserContexts:
    """Tests for the get_all_user_contexts storage method."""

    @pytest.fixture
    async def storage(self, tmp_path) -> SQLiteTaskStorage:
        """Create an initialized SQLite storage for testing.

        Args:
            tmp_path: Pytest fixture providing a temporary directory path.

        Yields:
            SQLiteTaskStorage: An initialized storage instance for testing.
        """
        db_path = str(tmp_path / "test_contexts.db")
        storage = SQLiteTaskStorage(db_path=db_path)
        await storage.initialize()
        yield storage
        await storage.close()

    @pytest.mark.asyncio
    async def test_no_tasks(self, storage: SQLiteTaskStorage) -> None:
        """Verify get_all_user_contexts returns empty list when no tasks exist.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        contexts = await storage.get_all_user_contexts(date.today())
        assert contexts == []

    @pytest.mark.asyncio
    async def test_single_user_context(self, storage: SQLiteTaskStorage) -> None:
        """Verify get_all_user_contexts returns single context for one user.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        today = date.today()
        
        await storage.add_task(
            description="Test task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        
        contexts = await storage.get_all_user_contexts(today)
        
        assert len(contexts) == 1
        assert contexts[0] == (123, 456, 789)

    @pytest.mark.asyncio
    async def test_multiple_user_contexts(self, storage: SQLiteTaskStorage) -> None:
        """Verify get_all_user_contexts returns all unique user contexts.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        today = date.today()
        
        # Different users in same channel
        await storage.add_task(
            description="Task 1",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=111,
            task_date=today,
        )
        await storage.add_task(
            description="Task 2",
            priority=Priority.B,
            server_id=123,
            channel_id=456,
            user_id=222,
            task_date=today,
        )
        
        # Different channel
        await storage.add_task(
            description="Task 3",
            priority=Priority.C,
            server_id=123,
            channel_id=999,
            user_id=333,
            task_date=today,
        )
        
        contexts = await storage.get_all_user_contexts(today)
        
        assert len(contexts) == 3
        assert (123, 456, 111) in contexts
        assert (123, 456, 222) in contexts
        assert (123, 999, 333) in contexts

    @pytest.mark.asyncio
    async def test_returns_unique_contexts_only(self, storage: SQLiteTaskStorage) -> None:
        """Verify get_all_user_contexts does not return duplicate contexts.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        today = date.today()
        
        # Same user with multiple tasks
        await storage.add_task(
            description="Task 1",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        await storage.add_task(
            description="Task 2",
            priority=Priority.B,
            server_id=123,
            channel_id=456,
            user_id=789,
            task_date=today,
        )
        
        contexts = await storage.get_all_user_contexts(today)
        
        assert len(contexts) == 1
        assert contexts[0] == (123, 456, 789)

    @pytest.mark.asyncio
    async def test_filters_by_date(self, storage: SQLiteTaskStorage) -> None:
        """Verify get_all_user_contexts only returns contexts for the specified date.

        Args:
            storage: The SQLite storage fixture for testing.
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Task from yesterday
        await storage.add_task(
            description="Yesterday task",
            priority=Priority.A,
            server_id=123,
            channel_id=456,
            user_id=111,
            task_date=yesterday,
        )
        
        # Task from today
        await storage.add_task(
            description="Today task",
            priority=Priority.B,
            server_id=123,
            channel_id=456,
            user_id=222,
            task_date=today,
        )
        
        today_contexts = await storage.get_all_user_contexts(today)
        yesterday_contexts = await storage.get_all_user_contexts(yesterday)
        
        assert len(today_contexts) == 1
        assert (123, 456, 222) in today_contexts
        
        assert len(yesterday_contexts) == 1
        assert (123, 456, 111) in yesterday_contexts
