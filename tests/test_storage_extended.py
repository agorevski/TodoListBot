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
    """Create a temporary SQLite storage for testing.

    Yields:
        SQLiteTaskStorage: An initialized storage instance backed by a
            temporary database that is automatically cleaned up after the test.
    """
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
        """Test updating task description.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that updating only the description field works correctly
        while preserving other task attributes like priority.
        """
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
        """Test updating task priority.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that updating only the priority field works correctly.
        """
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
        """Test updating both description and priority.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that both description and priority can be updated
        simultaneously in a single update_task call.
        """
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
        """Test update with no changes returns False.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that calling update_task without providing any fields
        to update returns False to indicate no changes were made.
        """
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
        """Test update non-existent task returns False.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that attempting to update a task that doesn't exist
        returns False rather than raising an exception.
        """
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
        """Test cleanup removes old tasks.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that cleanup_old_tasks removes tasks older than the
        specified retention period while preserving recent and current tasks.
        """
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
        """Test cleanup with 0 days returns 0.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that cleanup is effectively disabled when retention_days
        is set to 0, returning 0 deleted tasks.
        """
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
        """Test cleanup with negative days returns 0.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that cleanup handles negative retention_days gracefully
        by returning 0 without deleting any tasks.
        """
        count = await storage.cleanup_old_tasks(retention_days=-5)
        assert count == 0


class TestGetStats:
    """Tests for get_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, storage):
        """Test stats on empty database.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that get_stats returns correct default values when
        the database contains no tasks.
        """
        stats = await storage.get_stats()

        assert stats["total_tasks"] == 0
        assert stats["unique_users"] == 0
        assert stats["schema_version"] == 2
        assert "database_path" in stats

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, storage):
        """Test stats with tasks.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that get_stats correctly counts total tasks and
        unique users when tasks exist in the database.
        """
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
        assert stats["schema_version"] == 2


class TestMigrations:
    """Tests for database migrations."""

    @pytest.mark.asyncio
    async def test_initialize_creates_schema_version(self):
        """Test initialize creates schema_version table.

        Verifies that initializing a new database creates the
        schema_version table with the current schema version.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = SQLiteTaskStorage(db_path=db_path)
            try:
                await storage.initialize()

                stats = await storage.get_stats()
                assert stats["schema_version"] == 2
            finally:
                await storage.close()

    @pytest.mark.asyncio
    async def test_reinitialize_same_version(self):
        """Test re-initializing doesn't break existing data.

        Verifies that closing and re-opening a storage instance
        preserves existing task data across initialization cycles.
        """
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


class TestWithRetryDecorator:
    """Tests for the with_retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retry decorator retries on transient failures.

        Verifies that the with_retry decorator automatically retries
        operations that fail with transient aiosqlite errors until
        they eventually succeed.
        """
        import aiosqlite

        from todo_bot.storage.sqlite import with_retry

        call_count = 0

        @with_retry(max_retries=2, delay=0.01)
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiosqlite.Error("Transient error")
            return "success"

        result = await flaky_operation()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry decorator raises after max retries.

        Verifies that when all retry attempts are exhausted, the
        decorator raises a StorageOperationError wrapping the
        original failure.
        """
        import aiosqlite

        from todo_bot.exceptions import StorageOperationError  # noqa: F401
        from todo_bot.storage.sqlite import with_retry

        call_count = 0

        @with_retry(max_retries=2, delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise aiosqlite.Error("Persistent error")

        with pytest.raises(StorageOperationError, match="failed after"):
            await always_fails()

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_success_first_try(self):
        """Test retry decorator succeeds on first try.

        Verifies that the with_retry decorator does not interfere
        with operations that succeed immediately on the first attempt.
        """
        from todo_bot.storage.sqlite import with_retry

        call_count = 0

        @with_retry(max_retries=2, delay=0.01)
        async def succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await succeeds()
        assert result == "success"
        assert call_count == 1


class TestStorageLayerValidation:
    """Tests for defense-in-depth validation in the storage layer."""

    @pytest.mark.asyncio
    async def test_add_task_rejects_empty_description(self, storage):
        """Test that add_task rejects empty descriptions.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that the storage layer validates descriptions and
        raises ValidationError for empty strings.
        """
        from todo_bot.exceptions import ValidationError

        with pytest.raises(ValidationError, match="description is required"):
            await storage.add_task(
                description="",
                priority=Priority.A,
                server_id=1,
                channel_id=1,
                user_id=1,
            )

    @pytest.mark.asyncio
    async def test_add_task_rejects_whitespace_only_description(self, storage):
        """Test that add_task rejects whitespace-only descriptions.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that descriptions containing only whitespace are
        rejected after stripping, as they would be effectively empty.
        """
        from todo_bot.exceptions import ValidationError

        with pytest.raises(ValidationError, match="at least 1 character"):
            await storage.add_task(
                description="   ",
                priority=Priority.A,
                server_id=1,
                channel_id=1,
                user_id=1,
            )

    @pytest.mark.asyncio
    async def test_add_task_rejects_too_long_description(self, storage):
        """Test that add_task rejects descriptions exceeding max length.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that descriptions longer than MAX_DESCRIPTION_LENGTH
        are rejected with a ValidationError.
        """
        from todo_bot.config import MAX_DESCRIPTION_LENGTH
        from todo_bot.exceptions import ValidationError

        long_description = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValidationError, match="too long"):
            await storage.add_task(
                description=long_description,
                priority=Priority.A,
                server_id=1,
                channel_id=1,
                user_id=1,
            )

    @pytest.mark.asyncio
    async def test_add_task_strips_whitespace(self, storage):
        """Test that add_task strips leading/trailing whitespace.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that whitespace is stripped from descriptions before
        storage, ensuring clean data.
        """
        task = await storage.add_task(
            description="  Valid task  ",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        assert task.description == "Valid task"

    @pytest.mark.asyncio
    async def test_add_task_accepts_valid_description(self, storage):
        """Test that add_task accepts valid descriptions.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that valid descriptions are accepted and the task
        is created with the correct attributes.
        """
        task = await storage.add_task(
            description="Valid task description",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        assert task.description == "Valid task description"
        assert task.id is not None

    @pytest.mark.asyncio
    async def test_update_task_rejects_empty_description(self, storage):
        """Test that update_task rejects empty descriptions.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that update_task validates the new description and
        raises ValidationError for empty strings.
        """
        from todo_bot.exceptions import ValidationError

        task = await storage.add_task(
            description="Original",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        with pytest.raises(ValidationError, match="description is required"):
            await storage.update_task(
                task_id=task.id,
                server_id=1,
                channel_id=1,
                user_id=1,
                description="",
            )

    @pytest.mark.asyncio
    async def test_update_task_rejects_too_long_description(self, storage):
        """Test that update_task rejects descriptions exceeding max length.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that update_task validates description length and
        raises ValidationError when it exceeds MAX_DESCRIPTION_LENGTH.
        """
        from todo_bot.config import MAX_DESCRIPTION_LENGTH
        from todo_bot.exceptions import ValidationError

        task = await storage.add_task(
            description="Original",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        long_description = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(ValidationError, match="too long"):
            await storage.update_task(
                task_id=task.id,
                server_id=1,
                channel_id=1,
                user_id=1,
                description=long_description,
            )

    @pytest.mark.asyncio
    async def test_update_task_strips_whitespace(self, storage):
        """Test that update_task strips leading/trailing whitespace.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that whitespace is stripped from updated descriptions
        before storage.
        """
        task = await storage.add_task(
            description="Original",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        await storage.update_task(
            task_id=task.id,
            server_id=1,
            channel_id=1,
            user_id=1,
            description="  Updated task  ",
        )

        updated = await storage.get_task_by_id(task.id, 1, 1, 1)
        assert updated.description == "Updated task"

    @pytest.mark.asyncio
    async def test_update_task_priority_only_skips_description_validation(self, storage):
        """Test that update_task with only priority skips description validation.

        Args:
            storage: The SQLiteTaskStorage fixture instance.

        Verifies that when only updating priority (no description provided),
        description validation is skipped and the original description is
        preserved.
        """
        task = await storage.add_task(
            description="Original",
            priority=Priority.A,
            server_id=1,
            channel_id=1,
            user_id=1,
        )

        # Should not raise - no description provided, only priority
        result = await storage.update_task(
            task_id=task.id,
            server_id=1,
            channel_id=1,
            user_id=1,
            priority=Priority.C,
        )

        assert result is True
        updated = await storage.get_task_by_id(task.id, 1, 1, 1)
        assert updated.priority == Priority.C
        assert updated.description == "Original"
