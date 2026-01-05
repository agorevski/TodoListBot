"""Tests for the ViewRegistry class."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from tests.conftest import TEST_CHANNEL_ID, TEST_SERVER_ID, TEST_USER_ID
from todo_bot.models.task import Priority, Task
from todo_bot.views.registry import ViewRegistry
from todo_bot.views.task_view import TaskListView


def create_task(
    id: int = 1,
    description: str = "Test task",
    priority: Priority = Priority.A,
    done: bool = False,
    task_date: date | None = None,
) -> Task:
    """Create a task instance for testing purposes.

    Args:
        id: The unique identifier for the task.
        description: The task description text.
        priority: The priority level of the task.
        done: Whether the task is marked as complete.
        task_date: The date associated with the task. Defaults to today.

    Returns:
        A Task instance configured with the specified parameters and
        test-specific server, channel, and user IDs.
    """
    return Task(
        id=id,
        description=description,
        priority=priority,
        server_id=TEST_SERVER_ID,
        channel_id=TEST_CHANNEL_ID,
        user_id=TEST_USER_ID,
        done=done,
        task_date=task_date or date.today(),
    )


class TestViewRegistry:
    """Tests for ViewRegistry class."""

    def test_registry_initialization(self) -> None:
        """Test that a new ViewRegistry initializes with no registered views.

        Verifies that both view count and key count are zero upon creation.
        """
        registry = ViewRegistry()
        assert registry.get_view_count() == 0
        assert registry.get_key_count() == 0

    @pytest.mark.asyncio
    async def test_register_view(self) -> None:
        """Test that a TaskListView auto-registers with the registry on init.

        Verifies that creating a TaskListView with a registry parameter
        automatically registers the view, incrementing both view and key counts.
        """
        registry = ViewRegistry()
        storage = MagicMock()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        # View should auto-register in __init__
        assert registry.get_view_count() == 1
        assert registry.get_key_count() == 1

    @pytest.mark.asyncio
    async def test_register_multiple_views_same_key(self) -> None:
        """Test registering multiple views with identical key parameters.

        Verifies that multiple views with the same server, channel, user,
        and date are grouped under a single key, resulting in multiple
        views but only one key entry.
        """
        registry = ViewRegistry()
        storage = MagicMock()
        task_date = date.today()

        view1 = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            task_date=task_date,
            registry=registry,
        )

        view2 = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            task_date=task_date,
            registry=registry,
        )

        # Both views should be registered under the same key
        assert registry.get_view_count() == 2
        assert registry.get_key_count() == 1

    @pytest.mark.asyncio
    async def test_register_views_different_keys(self) -> None:
        """Test registering views with different key parameters.

        Verifies that views with different user IDs are registered under
        separate keys, resulting in distinct key entries for each view.
        """
        registry = ViewRegistry()
        storage = MagicMock()

        view1 = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        view2 = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID + 1,  # Different user
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        assert registry.get_view_count() == 2
        assert registry.get_key_count() == 2

    @pytest.mark.asyncio
    async def test_unregister_view(self) -> None:
        """Test that unregistering a view removes it from the registry.

        Verifies that after unregistering, both the view count and key
        count return to zero when the last view under a key is removed.
        """
        registry = ViewRegistry()
        storage = MagicMock()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        assert registry.get_view_count() == 1

        registry.unregister(view)

        assert registry.get_view_count() == 0
        assert registry.get_key_count() == 0

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_view(self) -> None:
        """Test that unregistering a non-registered view does not raise.

        Verifies that calling unregister on a view that was never registered
        (created without a registry parameter) completes without error.
        """
        registry = ViewRegistry()
        storage = MagicMock()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            # No registry passed, so not registered
        )

        # Should not raise
        registry.unregister(view)
        assert registry.get_view_count() == 0

    @pytest.mark.asyncio
    async def test_notify_no_views(self) -> None:
        """Test that notify returns zero when no views are registered.

        Verifies that calling notify on an empty registry returns a count
        of zero indicating no views were refreshed.
        """
        registry = ViewRegistry()

        count = await registry.notify(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=date.today(),
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_notify_with_views(self) -> None:
        """Test that notify refreshes all matching registered views.

        Verifies that notify triggers storage.get_tasks and message.edit
        for views matching the notification parameters, returning the
        count of successfully refreshed views.
        """
        registry = ViewRegistry()
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])
        task_date = date.today()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            task_date=task_date,
            registry=registry,
        )

        # Set up message for refresh
        message = MagicMock()
        message.edit = AsyncMock()
        view.set_message(message)

        count = await registry.notify(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=task_date,
        )

        assert count == 1
        storage.get_tasks.assert_called_once()
        message.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_different_date(self) -> None:
        """Test that notify does not refresh views with non-matching dates.

        Verifies that a view registered for one date is not refreshed when
        notify is called with a different date, ensuring key-based filtering
        works correctly.
        """
        registry = ViewRegistry()
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            task_date=date(2024, 1, 1),  # Specific date
            registry=registry,
        )

        message = MagicMock()
        message.edit = AsyncMock()
        view.set_message(message)

        # Notify for different date
        count = await registry.notify(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=date(2024, 1, 2),  # Different date
        )

        assert count == 0
        storage.get_tasks.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_removes_failed_views(self) -> None:
        """Test that notify handles storage errors without removing views.

        Verifies that when a storage error occurs during refresh, the view
        remains registered since storage errors may be transient. Only
        Discord errors (indicating invalid views) should cause removal.
        """
        from todo_bot.exceptions import StorageError

        registry = ViewRegistry()
        storage = MagicMock()
        # Simulate a storage error when getting tasks - this will propagate
        storage.get_tasks = AsyncMock(side_effect=StorageError("Database connection lost"))
        task_date = date.today()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            task_date=task_date,
            registry=registry,
        )

        message = MagicMock()
        message.edit = AsyncMock()
        view.set_message(message)

        assert registry.get_view_count() == 1

        # This should log the storage error but NOT remove the view
        # (only Discord errors cause removal since they indicate the view is invalid)
        count = await registry.notify(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=task_date,
        )

        # Storage errors don't cause view removal (view may recover)
        assert count == 0
        assert registry.get_view_count() == 1  # View still registered

    @pytest.mark.asyncio
    async def test_cleanup_empty_entries(self) -> None:
        """Test that cleanup removes empty key entries from the registry.

        Verifies that after unregistering a view, the key entry is
        automatically cleaned up, and subsequent cleanup calls return
        zero removed entries.
        """
        registry = ViewRegistry()
        storage = MagicMock()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        registry.unregister(view)

        # After unregistering, the entry should already be cleaned
        assert registry.get_key_count() == 0

        # Cleanup should return 0 since already cleaned
        removed = registry.cleanup()
        assert removed == 0

    def test_make_key(self) -> None:
        """Test that _make_key creates the correct tuple key.

        Verifies that the key is a tuple of (server_id, channel_id,
        user_id, task_date) matching the provided parameters.
        """
        registry = ViewRegistry()
        task_date = date(2024, 6, 15)

        key = registry._make_key(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=task_date,
        )

        assert key == (TEST_SERVER_ID, TEST_CHANNEL_ID, TEST_USER_ID, task_date)


class TestTaskListViewRegistration:
    """Tests for TaskListView registry integration."""

    @pytest.mark.asyncio
    async def test_view_registers_on_init(self) -> None:
        """Test that TaskListView registers itself during initialization.

        Verifies that when a registry is provided to the TaskListView
        constructor, the view is automatically registered.
        """
        registry = ViewRegistry()
        storage = MagicMock()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        assert registry.get_view_count() == 1

    @pytest.mark.asyncio
    async def test_view_unregisters_on_timeout(self) -> None:
        """Test that TaskListView unregisters itself when it times out.

        Verifies that calling on_timeout removes the view from the
        registry, preventing stale views from being notified.
        """
        registry = ViewRegistry()
        storage = MagicMock()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        assert registry.get_view_count() == 1

        await view.on_timeout()

        assert registry.get_view_count() == 0

    @pytest.mark.asyncio
    async def test_refresh_from_storage_no_message(self) -> None:
        """Test that refresh_from_storage returns early with no message.

        Verifies that when no message is set on the view, the refresh
        operation exits early without calling storage.get_tasks.
        """
        registry = ViewRegistry()
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        # No message set, should return early
        await view.refresh_from_storage()

        # get_tasks should not be called since there's no message
        storage.get_tasks.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_from_storage_success(self) -> None:
        """Test that refresh_from_storage updates the view with new tasks.

        Verifies that the refresh operation fetches tasks from storage,
        updates the view's task list, and edits the Discord message.
        """
        registry = ViewRegistry()
        storage = MagicMock()
        task = create_task()
        storage.get_tasks = AsyncMock(return_value=[task])

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        message = MagicMock()
        message.edit = AsyncMock()
        view.set_message(message)

        await view.refresh_from_storage()

        storage.get_tasks.assert_called_once()
        message.edit.assert_called_once()
        assert len(view.tasks) == 1

    @pytest.mark.asyncio
    async def test_refresh_from_storage_message_deleted(self) -> None:
        """Test that refresh_from_storage handles deleted messages gracefully.

        Verifies that when a Discord NotFound error occurs (message deleted),
        the view is automatically unregistered from the registry.
        """
        import discord

        registry = ViewRegistry()
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        message = MagicMock()
        message.edit = AsyncMock(
            side_effect=discord.errors.NotFound(MagicMock(), "Not found")
        )
        view.set_message(message)

        assert registry.get_view_count() == 1

        # Should not raise and should unregister
        await view.refresh_from_storage()

        assert registry.get_view_count() == 0

    @pytest.mark.asyncio
    async def test_refresh_from_storage_rate_limited(self) -> None:
        """Test that refresh_from_storage handles rate limiting gracefully.

        Verifies that when a Discord 429 rate limit error occurs, the view
        remains registered (since rate limits are transient) and no
        exception is raised.
        """
        import discord

        registry = ViewRegistry()
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        mock_response = MagicMock()
        mock_response.status = 429
        http_error = discord.errors.HTTPException(mock_response, "Rate limited")
        http_error.status = 429

        message = MagicMock()
        message.edit = AsyncMock(side_effect=http_error)
        view.set_message(message)

        # Should not raise
        await view.refresh_from_storage()

        # View should still be registered
        assert registry.get_view_count() == 1

    @pytest.mark.asyncio
    async def test_refresh_from_storage_other_http_error(self) -> None:
        """Test that refresh_from_storage handles other HTTP errors gracefully.

        Verifies that when a non-rate-limit HTTP error (e.g., 500) occurs,
        the view remains registered and no exception is raised.
        """
        import discord

        registry = ViewRegistry()
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        mock_response = MagicMock()
        mock_response.status = 500
        http_error = discord.errors.HTTPException(mock_response, "Server error")
        http_error.status = 500

        message = MagicMock()
        message.edit = AsyncMock(side_effect=http_error)
        view.set_message(message)

        # Should not raise
        await view.refresh_from_storage()

        # View should still be registered
        assert registry.get_view_count() == 1

    @pytest.mark.asyncio
    async def test_view_without_registry(self) -> None:
        """Test that TaskListView works correctly without a registry.

        Verifies that a view created without a registry parameter can
        still handle timeout events without raising errors.
        """
        storage = MagicMock()

        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            # No registry
        )

        # Should not raise on timeout
        await view.on_timeout()

    @pytest.mark.asyncio
    async def test_create_task_list_view_with_registry(self) -> None:
        """Test that create_task_list_view factory passes registry correctly.

        Verifies that the factory function properly passes the registry
        parameter to the TaskListView constructor, resulting in automatic
        registration.
        """
        from todo_bot.views.task_view import create_task_list_view

        registry = ViewRegistry()
        storage = MagicMock()

        view = create_task_list_view(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            registry=registry,
        )

        assert view._registry is registry
        assert registry.get_view_count() == 1
