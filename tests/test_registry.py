"""Tests for the ViewRegistry class."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

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
    """Helper to create a task for testing."""
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
        """Test registry initializes empty."""
        registry = ViewRegistry()
        assert registry.get_view_count() == 0
        assert registry.get_key_count() == 0

    @pytest.mark.asyncio
    async def test_register_view(self) -> None:
        """Test registering a view."""
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
        """Test registering multiple views with the same key."""
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
        """Test registering views with different keys."""
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
        """Test unregistering a view."""
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
        """Test unregistering a view that was never registered."""
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
        """Test notify when no views are registered."""
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
        """Test notify refreshes registered views."""
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
        """Test notify doesn't affect views for different dates."""
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
        """Test notify removes views that fail to refresh."""
        registry = ViewRegistry()
        storage = MagicMock()
        storage.get_tasks = AsyncMock(side_effect=Exception("Test error"))
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

        # This should fail and remove the view
        count = await registry.notify(
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
            user_id=TEST_USER_ID,
            task_date=task_date,
        )

        assert count == 0
        assert registry.get_view_count() == 0

    @pytest.mark.asyncio
    async def test_cleanup_empty_entries(self) -> None:
        """Test cleanup removes empty entries."""
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
        """Test key creation."""
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
        """Test view registers itself on initialization."""
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
        """Test view unregisters itself on timeout."""
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
        """Test refresh_from_storage with no message set."""
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
        """Test successful refresh_from_storage."""
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
        """Test refresh_from_storage when message is deleted."""
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
        """Test refresh_from_storage when rate limited."""
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
        """Test refresh_from_storage with other HTTP error."""
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
        """Test view works without registry."""
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
        """Test create_task_list_view passes registry correctly."""
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
