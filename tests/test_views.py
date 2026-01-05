"""Tests for Discord UI views."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import TEST_CHANNEL_ID, TEST_SERVER_ID, TEST_USER_ID
from todo_bot.models.task import Priority, Task
from todo_bot.views.task_view import TaskButton, TaskListView, create_task_list_view


def create_task(
    id: int = 1,
    description: str = "Test task",
    priority: Priority = Priority.A,
    done: bool = False,
) -> Task:
    """Create a task instance for testing purposes.

    Args:
        id: The unique identifier for the task.
        description: The task description text.
        priority: The priority level of the task.
        done: Whether the task is marked as completed.

    Returns:
        A Task instance configured with test server, channel, and user IDs.
    """
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
        """Test that a button for an incomplete task displays correctly.

        Verifies that the button label contains 'Done #' prefix and
        that an emoji is present on the button.
        """
        task = create_task(id=5, done=False)
        storage = MagicMock()

        button = TaskButton(task=task, storage=storage, display_index=1)

        assert "Done #1" in button.label
        # Discord.py wraps emojis in PartialEmoji, check name instead
        assert button.emoji is not None

    @pytest.mark.asyncio
    async def test_button_completed_task(self) -> None:
        """Test that a button for a completed task shows 'Undo' label.

        Verifies that completed tasks display 'Undo' without a display
        number since they don't have display numbers in the task list.
        """
        task = create_task(id=3, done=True)
        storage = MagicMock()

        button = TaskButton(task=task, storage=storage, display_index=2)

        # Completed tasks show "Undo" without a number since they don't
        # have display numbers in the task list
        assert button.label == "Undo"
        assert button.emoji is not None

    @pytest.mark.asyncio
    async def test_button_custom_id_format(self) -> None:
        """Test that button custom_id follows the expected format.

        Verifies that the custom_id starts with 'task_' followed by the
        database ID for internal operations.
        """
        task = create_task(id=7)
        storage = MagicMock()

        button = TaskButton(task=task, storage=storage, display_index=1)

        # custom_id still uses database ID for internal operations
        assert button.custom_id.startswith("task_7_")

    @pytest.mark.asyncio
    async def test_button_callback_wrong_user(self) -> None:
        """Test that callback rejects clicks from a different user.

        Verifies that when a user who doesn't own the task clicks the
        button, an ephemeral error message is sent indicating they can
        only modify their own tasks.
        """
        task = create_task(id=1)
        storage = MagicMock()
        button = TaskButton(task=task, storage=storage, display_index=1)

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
        """Test that button callback successfully marks a task as done.

        Verifies that clicking the button on an incomplete task calls
        the storage's mark_task_done method and updates the task state.
        """
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
        """Test that button callback successfully marks a task as undone.

        Verifies that clicking the button on a completed task calls
        the storage's mark_task_undone method and updates the task state.
        """
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
        """Test button callback behavior when mark undone operation fails.

        Verifies that when storage.mark_task_undone returns False, an
        appropriate 'not found' error message is displayed to the user.
        """
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
        """Test button callback behavior when task update fails.

        Verifies that when storage.mark_task_done returns False, an
        appropriate 'not found' error message is displayed to the user.
        """
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
        """Test button callback when button is not attached to a view.

        Verifies that the callback handles the case where button.view is
        None gracefully, completing the storage operation without raising.
        """
        task = create_task(id=1, done=False)
        storage = MagicMock()
        storage.mark_task_done = AsyncMock(return_value=True)

        # Create button without adding to view
        button = TaskButton(task=task, storage=storage, display_index=1)

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
        """Test creating a TaskListView with an empty task list.

        Verifies that the view has no child buttons when created with
        no tasks.
        """
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
        """Test creating a TaskListView with multiple tasks.

        Verifies that the view creates one button per task when
        initialized with a list of tasks.
        """
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
        """Test that view respects Discord's 25 button limit.

        Verifies that when more than 25 tasks are provided, only the
        first 25 buttons are added to the view.
        """
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
        """Test that get_content returns formatted task list content.

        Verifies that the content includes the task description text.
        """
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
        """Test that refresh updates the view with latest task data.

        Verifies that refresh calls storage.get_tasks and edits the
        interaction message with updated content.
        """
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
        """Test that refresh handles deleted message gracefully.

        Verifies that when the message edit raises NotFound error,
        the refresh method does not raise an exception.
        """
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
        """Test that set_message stores the message reference.

        Verifies that the internal _message attribute is set correctly.
        """
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
        """Test that on_timeout disables all buttons in the view.

        Verifies that when the view times out, all button children are
        disabled and the message is edited to reflect this state.
        """
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
        """Test that on_timeout handles missing message gracefully.

        Verifies that when no message reference is set, the timeout
        method does not raise an exception.
        """
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
        """Test that on_timeout handles deleted message gracefully.

        Verifies that when the message edit raises NotFound error,
        the timeout method does not raise an exception.
        """
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
        """Test that create_task_list_view creates a properly configured view.

        Verifies that the helper function returns a TaskListView instance
        with correct user_id, server_id, and channel_id attributes.
        """
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


class TestViewHttpErrors:
    """Tests for HTTP error handling in views."""

    @pytest.mark.asyncio
    async def test_view_refresh_rate_limited(self) -> None:
        """Test that refresh handles rate limiting gracefully.

        Verifies that when the message edit raises HTTPException with
        status 429 (rate limited), the refresh method does not raise.
        """
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

        # Create a mock HTTPException with status 429
        mock_response = MagicMock()
        mock_response.status = 429
        http_error = discord.errors.HTTPException(mock_response, "Rate limited")
        http_error.status = 429

        interaction = MagicMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock(side_effect=http_error)

        # Should not raise
        await view.refresh(interaction)

    @pytest.mark.asyncio
    async def test_view_refresh_other_http_error(self) -> None:
        """Test that refresh handles other HTTP errors gracefully.

        Verifies that when the message edit raises HTTPException with
        status 500 (server error), the refresh method does not raise.
        """
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

        # Create a mock HTTPException with status 500
        mock_response = MagicMock()
        mock_response.status = 500
        http_error = discord.errors.HTTPException(mock_response, "Server error")
        http_error.status = 500

        interaction = MagicMock()
        interaction.message = MagicMock()
        interaction.message.edit = AsyncMock(side_effect=http_error)

        # Should not raise
        await view.refresh(interaction)

    @pytest.mark.asyncio
    async def test_view_on_timeout_rate_limited(self) -> None:
        """Test that on_timeout handles rate limiting gracefully.

        Verifies that when the message edit raises HTTPException with
        status 429 (rate limited), the timeout method does not raise.
        """
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

        # Create a mock HTTPException with status 429
        mock_response = MagicMock()
        mock_response.status = 429
        http_error = discord.errors.HTTPException(mock_response, "Rate limited")
        http_error.status = 429

        message = MagicMock()
        message.edit = AsyncMock(side_effect=http_error)
        view.set_message(message)

        # Should not raise
        await view.on_timeout()

    @pytest.mark.asyncio
    async def test_view_on_timeout_other_http_error(self) -> None:
        """Test that on_timeout handles other HTTP errors gracefully.

        Verifies that when the message edit raises HTTPException with
        status 500 (server error), the timeout method does not raise.
        """
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

        # Create a mock HTTPException with status 500
        mock_response = MagicMock()
        mock_response.status = 500
        http_error = discord.errors.HTTPException(mock_response, "Server error")
        http_error.status = 500

        message = MagicMock()
        message.edit = AsyncMock(side_effect=http_error)
        view.set_message(message)

        # Should not raise
        await view.on_timeout()
