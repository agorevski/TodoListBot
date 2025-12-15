"""Extended tests for SQLite storage covering new features."""

import os
import tempfile
from datetime import date, timedelta

import pytest
import pytest_asyncio

from todo_bot.models.task import Priority
from todo_bot.storage.sqlite import SQLiteTaskStorage


@pytest_asyncio.fixture
async def storage():
    """Create a temporary SQLite storage for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tasks.db")
        storage = SQLiteTaskStorage(db_path=db_path)
        await storage.initialize()
        yield storage
        await storage.close()


class TestUpdateTask:
    """Tests for update_task method."""

    @pytest.mark.asyncio
    async def test_update_task_description(self, storage):
        """Test updating task description."""
        task = await storage.add_task(
            description="Original",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        result = await storage.update_task(
            task_id=task.id,
            server_id=1,
            channel_id=1,
            user_id=1,
            description="Updated",
        )

        assert result is True
        updated = await storage.get_task_by_id(task.id, 1, 1, 1)
        assert updated.description == "Updated"
        assert updated.priority == Priority.A

    @pytest.mark.asyncio
    async def test_update_task_priority(self, storage):
        """Test updating task priority."""
        task = await storage.add_task(
            description="Test",
            priority=Priority.C,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        result = await storage.update_task(
            task_id=task.id,
            server_id=1,
            channel_id=1,
            user_id=1,
            priority=Priority.A,
        )

        assert result is True
        updated = await storage.get_task_by_id(task.id, 1, 1, 1)
        assert updated.priority == Priority.A

    @pytest.mark.asyncio
    async def test_update_task_both(self, storage):
        """Test updating both description and priority."""
        task = await storage.add_task(
            description="Original",
            priority=Priority.C,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        result = await storage.update_task(
            task_id=task.id,
            server_id=1,
            channel_id=1,
            user_id=1,
            description="Updated",
            priority=Priority.A,
        )

        assert result is True
        updated = await storage.get_task_by_id(task.id, 1, 1, 1)
        assert updated.description == "Updated"
        assert updated.priority == Priority.A

    @pytest.mark.asyncio
    async def test_update_task_nothing(self, storage):
        """Test update with no changes returns False."""
        task = await storage.add_task(
            description="Test",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        result = await storage.update_task(
            task_id=task.id,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, storage):
        """Test update non-existent task returns False."""
        result = await storage.update_task(
            task_id=9999,
            server_id=1,
            channel_id=1,
            user_id=1,
            description="Updated",
        )

        assert result is False


class TestCleanupOldTasks:
    """Tests for cleanup_old_tasks method."""

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(self, storage):
        """Test cleanup removes old tasks."""
        old_date = date.today() - timedelta(days=10)
        recent_date = date.today() - timedelta(days=2)

        # Add old task
        await storage.add_task(
            description="Old task",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
            task_date=old_date,
        )

        # Add recent task
        await storage.add_task(
            description="Recent task",
            priority=Priority.B,
            server_id=1,
            channel_id=1,
            user_id=1,
            task_date=recent_date,
        )

        # Add today's task
        await storage.add_task(
            description="Today's task",
            priority=Priority.C,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        # Cleanup tasks older than 5 days
        count = await storage.cleanup_old_tasks(retention_days=5)

        assert count == 1  # Only old task removed

        # Verify recent and today's tasks remain
        old_tasks = await storage.get_tasks(1, 1, 1, old_date)
        recent_tasks = await storage.get_tasks(1, 1, 1, recent_date)
        today_tasks = await storage.get_tasks(1, 1, 1, date.today())

        assert len(old_tasks) == 0
        assert len(recent_tasks) == 1
        assert len(today_tasks) == 1

    @pytest.mark.asyncio
    async def test_cleanup_disabled(self, storage):
        """Test cleanup with 0 days returns 0."""
        await storage.add_task(
            description="Test",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
            task_date=date.today() - timedelta(days=100),
        )

        count = await storage.cleanup_old_tasks(retention_days=0)

        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_negative(self, storage):
        """Test cleanup with negative days returns 0."""
        count = await storage.cleanup_old_tasks(retention_days=-5)
        assert count == 0


class TestGetStats:
    """Tests for get_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, storage):
        """Test stats on empty database."""
        stats = await storage.get_stats()

        assert stats["total_tasks"] == 0
        assert stats["unique_users"] == 0
        assert stats["schema_version"] == 1
        assert "database_path" in stats

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, storage):
        """Test stats with tasks."""
        # Add tasks from different users
        await storage.add_task(
            description="Task 1",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )
        await storage.add_task(
            description="Task 2",
            priority=Priority.B,
            server_id=1,
            channel_id=1,
            user_id=1,
        )
        await storage.add_task(
            description="Task 3",
            priority=Priority.C,
            server_id=1,
            channel_id=1,
            user_id=2,
        )

        stats = await storage.get_stats()

        assert stats["total_tasks"] == 3
        assert stats["unique_users"] == 2
        assert stats["schema_version"] == 1


class TestMigrations:
    """Tests for database migrations."""

    @pytest.mark.asyncio
    async def test_initialize_creates_schema_version(self):
        """Test initialize creates schema_version table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = SQLiteTaskStorage(db_path=db_path)
            await storage.initialize()

            stats = await storage.get_stats()
            assert stats["schema_version"] == 1

            await storage.close()

    @pytest.mark.asyncio
    async def test_reinitialize_same_version(self):
        """Test re-initializing doesn't break existing data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")

            # First initialization
            storage1 = SQLiteTaskStorage(db_path=db_path)
            await storage1.initialize()
            await storage1.add_task("Test", Priority.A, 1, 1, 1)
            await storage1.close()

            # Second initialization
            storage2 = SQLiteTaskStorage(db_path=db_path)
            await storage2.initialize()

            tasks = await storage2.get_tasks(1, 1, 1)
            assert len(tasks) == 1
            assert tasks[0].description == "Test"

            await storage2.close()
