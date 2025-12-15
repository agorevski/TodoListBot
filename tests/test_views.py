"""Tests for Discord UI views."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from todo_bot.models.task import Priority, Task
from todo_bot.views.task_view import TaskButton, TaskListView, create_task_list_view

# Test constants
TEST_SERVER_ID = 123456789
TEST_CHANNEL_ID = 987654321
TEST_USER_ID = 111222333


def create_task(
    id: int = 1,
    description: str = "Test task",
    priority: Priority = Priority.A,
    done: bool = False,
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
    )


class TestTaskButton:
    """Tests for TaskButton class."""

    @pytest.mark.asyncio
    async def test_button_incomplete_task(self) -> None:
        """Test button for incomplete task."""
        task = create_task(id=5, done=False)
        storage = MagicMock()

        button = TaskButton(task=task, storage=storage)

        assert "Done #5" in button.label
        # Discord.py wraps emojis in PartialEmoji, check name instead
        assert button.emoji is not None

    @pytest.mark.asyncio
    async def test_button_completed_task(self) -> None:
        """Test button for completed task."""
        task = create_task(id=3, done=True)
        storage = MagicMock()

        button = TaskButton(task=task, storage=storage)

        assert "Undo #3" in button.label
        assert button.emoji is not None

    @pytest.mark.asyncio
    async def test_button_custom_id_format(self) -> None:
        """Test that button custom_id is properly formatted."""
        task = create_task(id=7)
        storage = MagicMock()

        button = TaskButton(task=task, storage=storage)

        assert button.custom_id.startswith("task_7_")

    @pytest.mark.asyncio
    async def test_button_callback_wrong_user(self) -> None:
        """Test that callback rejects clicks from wrong user."""
        task = create_task(id=1)
        storage = MagicMock()
        button = TaskButton(task=task, storage=storage)

        # Mock interaction from different user
        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.id = 999999  # Different user
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        await button.callback(interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "only modify your own tasks" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_button_callback_mark_done(self) -> None:
        """Test button callback marks task as done."""
        task = create_task(id=1, done=False)
        storage = MagicMock()
        storage.mark_task_done = AsyncMock(return_value=True)
        storage.get_tasks = AsyncMock(return_value=[])

        # Create a real TaskListView and get the button from it
        view = TaskListView(
            tasks=[task],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        # Get the button that was added to the view
        button = list(view.children)[0]

        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.id = TEST_USER_ID
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock()

        await button.callback(interaction)

        storage.mark_task_done.assert_called_once()
        assert task.done is True
        interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_button_callback_mark_undone(self) -> None:
        """Test button callback marks task as undone."""
        task = create_task(id=1, done=True)
        storage = MagicMock()
        storage.mark_task_undone = AsyncMock(return_value=True)
        storage.get_tasks = AsyncMock(return_value=[])

        # Create a real TaskListView and get the button from it
        view = TaskListView(
            tasks=[task],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        # Get the button that was added to the view
        button = list(view.children)[0]

        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.id = TEST_USER_ID
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock()

        await button.callback(interaction)

        storage.mark_task_undone.assert_called_once()
        assert task.done is False

    @pytest.mark.asyncio
    async def test_button_callback_mark_undone_fails(self) -> None:
        """Test button callback when mark undone fails."""
        task = create_task(id=1, done=True)
        storage = MagicMock()
        storage.mark_task_undone = AsyncMock(return_value=False)
        storage.get_tasks = AsyncMock(return_value=[])

        # Create a real TaskListView and get the button from it
        view = TaskListView(
            tasks=[task],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        # Get the button that was added to the view
        button = list(view.children)[0]

        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.id = TEST_USER_ID
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock()

        await button.callback(interaction)

        storage.mark_task_undone.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "not found" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_button_callback_task_not_found(self) -> None:
        """Test button callback when task update fails."""
        task = create_task(id=1, done=False)
        storage = MagicMock()
        storage.mark_task_done = AsyncMock(return_value=False)
        storage.get_tasks = AsyncMock(return_value=[])

        # Create a real TaskListView and get the button from it
        view = TaskListView(
            tasks=[task],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        # Get the button that was added to the view
        button = list(view.children)[0]

        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.id = TEST_USER_ID
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock()

        await button.callback(interaction)

        call_args = interaction.response.send_message.call_args
        assert "not found" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_button_callback_no_view(self) -> None:
        """Test button callback when button is not attached to a view."""
        task = create_task(id=1, done=False)
        storage = MagicMock()
        storage.mark_task_done = AsyncMock(return_value=True)

        # Create button without adding to view
        button = TaskButton(task=task, storage=storage)

        interaction = MagicMock()
        interaction.user = MagicMock()
        interaction.user.id = TEST_USER_ID
        interaction.response = AsyncMock()
        interaction.response.send_message = AsyncMock()

        # Should not raise, just not refresh
        await button.callback(interaction)

        storage.mark_task_done.assert_called_once()
        # The button.view will be None since it's not added to a view
        # This tests the `if self.view is not None` branch


class TestTaskListView:
    """Tests for TaskListView class."""

    @pytest.mark.asyncio
    async def test_view_creation_empty(self) -> None:
        """Test creating view with no tasks."""
        storage = MagicMock()
        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        assert len(list(view.children)) == 0

    @pytest.mark.asyncio
    async def test_view_creation_with_tasks(self) -> None:
        """Test creating view with tasks adds buttons."""
        tasks = [create_task(id=1), create_task(id=2)]
        storage = MagicMock()

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        assert len(list(view.children)) == 2

    @pytest.mark.asyncio
    async def test_view_max_buttons(self) -> None:
        """Test that view limits to 25 buttons."""
        tasks = [create_task(id=i) for i in range(30)]
        storage = MagicMock()

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        assert len(list(view.children)) == 25

    @pytest.mark.asyncio
    async def test_view_get_content(self) -> None:
        """Test getting formatted content."""
        tasks = [create_task(description="Test task")]
        storage = MagicMock()

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        content = view.get_content()
        assert "Test task" in content

    @pytest.mark.asyncio
    async def test_view_refresh(self) -> None:
        """Test refreshing the view."""
        tasks = [create_task(id=1)]
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[create_task(id=1, done=True)])

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        interaction = MagicMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock()

        await view.refresh(interaction)

        storage.get_tasks.assert_called_once()
        interaction.message.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_view_refresh_message_deleted(self) -> None:
        """Test refresh when message was deleted."""
        import discord

        tasks = [create_task(id=1)]
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        interaction = MagicMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock(
            side_effect=discord.errors.NotFound(MagicMock(), "Not found")
        )

        # Should not raise
        await view.refresh(interaction)

    @pytest.mark.asyncio
    async def test_view_set_message(self) -> None:
        """Test setting message reference."""
        storage = MagicMock()
        view = TaskListView(
            tasks=[],
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        message = MagicMock()
        view.set_message(message)

        assert view._message == message

    @pytest.mark.asyncio
    async def test_view_on_timeout(self) -> None:
        """Test timeout disables buttons."""
        import discord

        tasks = [create_task(id=1)]
        storage = MagicMock()

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        message = MagicMock()
        message.edit = AsyncMock()
        view.set_message(message)

        await view.on_timeout()

        for child in view.children:
            if isinstance(child, discord.ui.Button):
                assert child.disabled is True

        message.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_view_on_timeout_no_message(self) -> None:
        """Test timeout when no message is set."""
        tasks = [create_task(id=1)]
        storage = MagicMock()

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        # Should not raise
        await view.on_timeout()

    @pytest.mark.asyncio
    async def test_view_on_timeout_message_deleted(self) -> None:
        """Test timeout when message was deleted."""
        import discord

        tasks = [create_task(id=1)]
        storage = MagicMock()

        view = TaskListView(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        message = MagicMock()
        message.edit = AsyncMock(
            side_effect=discord.errors.NotFound(MagicMock(), "Not found")
        )
        view.set_message(message)

        # Should not raise
        await view.on_timeout()


class TestCreateTaskListView:
    """Tests for create_task_list_view helper function."""

    @pytest.mark.asyncio
    async def test_create_view(self) -> None:
        """Test creating a view with helper function."""
        tasks = [create_task(id=1)]
        storage = MagicMock()

        view = create_task_list_view(
            tasks=tasks,
            storage=storage,
            user_id=TEST_USER_ID,
            server_id=TEST_SERVER_ID,
            channel_id=TEST_CHANNEL_ID,
        )

        assert isinstance(view, TaskListView)
        assert view.user_id == TEST_USER_ID
        assert view.server_id == TEST_SERVER_ID
        assert view.channel_id == TEST_CHANNEL_ID
