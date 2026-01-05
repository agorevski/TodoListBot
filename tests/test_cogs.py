"""Tests for Discord cogs (slash commands)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import TEST_CHANNEL_ID, TEST_SERVER_ID, TEST_USER_ID
from todo_bot.cogs.tasks import TasksCog
from todo_bot.models.task import MAX_DESCRIPTION_LENGTH, Priority, Task


def create_task(
    id: int = 1,
    description: str = "Test task",
    priority: Priority = Priority.A,
    done: bool = False,
) -> Task:
    """Create a Task instance for testing.

    Args:
        id: The unique identifier for the task.
        description: The task description text.
        priority: The priority level of the task.
        done: Whether the task is marked as complete.

    Returns:
        A Task instance configured with test server/channel/user IDs.
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


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock Discord bot.

    Returns:
        A MagicMock object representing a Discord bot instance.
    """
    return MagicMock()


@pytest.fixture
def mock_storage() -> MagicMock:
    """Create a mock storage backend.

    Returns:
        A MagicMock with async methods for task storage operations.
    """
    storage = MagicMock()
    storage.add_task = AsyncMock()
    storage.get_tasks = AsyncMock(return_value=[])
    storage.get_task_by_id = AsyncMock()
    storage.mark_task_done = AsyncMock(return_value=True)
    storage.delete_task = AsyncMock(return_value=True)
    storage.clear_completed_tasks = AsyncMock(return_value=0)
    return storage


@pytest.fixture
def cog(mock_bot: MagicMock, mock_storage: MagicMock) -> TasksCog:
    """Create a TasksCog instance for testing.

    Args:
        mock_bot: The mock Discord bot instance.
        mock_storage: The mock storage backend.

    Returns:
        A TasksCog instance configured with mock dependencies.
    """
    return TasksCog(mock_bot, mock_storage)


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create a mock Discord interaction.

    Returns:
        A MagicMock representing a Discord slash command interaction
        with pre-configured guild, channel, user, and response attributes.
    """
    interaction = MagicMock()
    interaction.guild = MagicMock()
    interaction.guild.id = TEST_SERVER_ID
    interaction.channel_id = TEST_CHANNEL_ID
    interaction.user = MagicMock()
    interaction.user.id = TEST_USER_ID
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.original_response = AsyncMock()
    return interaction


class TestAddTaskCommand:
    """Tests for /add command."""

    @pytest.mark.asyncio
    async def test_add_task_success(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test successfully adding a task.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        task = create_task(id=1, description="New task")
        mock_storage.add_task.return_value = task

        await cog.add_task.callback(cog, mock_interaction, "A", "New task")

        mock_storage.add_task.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Added task #1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_add_task_no_guild(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test adding task outside of a server.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        mock_interaction.guild = None

        await cog.add_task.callback(cog, mock_interaction, "A", "Task")

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "only be used in a server" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_add_task_invalid_priority(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test adding task with invalid priority.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        await cog.add_task.callback(cog, mock_interaction, "X", "Task")

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Invalid priority" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_add_task_description_too_long(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test adding task with description exceeding max length.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        long_desc = "x" * (MAX_DESCRIPTION_LENGTH + 1)

        await cog.add_task.callback(cog, mock_interaction, "A", long_desc)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "too long" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True


class TestListTasksCommand:
    """Tests for /list command."""

    @pytest.mark.asyncio
    async def test_list_tasks_empty(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test listing tasks when empty.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        mock_storage.get_tasks.return_value = []
        mock_interaction.original_response.return_value = MagicMock()

        await cog.list_tasks.callback(cog, mock_interaction, None)

        mock_storage.get_tasks.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_with_date(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test listing tasks for specific date.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        mock_storage.get_tasks.return_value = []
        mock_interaction.original_response.return_value = MagicMock()

        await cog.list_tasks.callback(cog, mock_interaction, "2024-12-25")

        call_kwargs = mock_storage.get_tasks.call_args[1]
        assert call_kwargs["task_date"] == date(2024, 12, 25)

    @pytest.mark.asyncio
    async def test_list_tasks_invalid_date(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test listing tasks with invalid date format.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        await cog.list_tasks.callback(cog, mock_interaction, "invalid-date")

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Invalid date format" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_list_tasks_no_guild(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test listing tasks outside of a server.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        mock_interaction.guild = None

        await cog.list_tasks.callback(cog, mock_interaction, None)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "only be used in a server" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_list_tasks_with_tasks(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test listing tasks when tasks exist.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        tasks = [create_task(id=1, description="Task 1")]
        mock_storage.get_tasks.return_value = tasks
        mock_interaction.original_response.return_value = MagicMock()

        await cog.list_tasks.callback(cog, mock_interaction, None)

        mock_interaction.response.send_message.assert_called_once()
        call_kwargs = mock_interaction.response.send_message.call_args[1]
        assert call_kwargs["view"] is not None


class TestMarkDoneCommand:
    """Tests for /done command."""

    @pytest.mark.asyncio
    async def test_mark_done_success(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test successfully marking task as done.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        task = create_task(id=1)
        mock_storage.get_task_by_id.return_value = task
        mock_storage.mark_task_done.return_value = True

        await cog.mark_done.callback(cog, mock_interaction, 1)

        mock_storage.mark_task_done.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "marked as done" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True  # Success should be ephemeral

    @pytest.mark.asyncio
    async def test_mark_done_not_found(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test marking non-existent task as done.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        mock_storage.get_task_by_id.return_value = None

        await cog.mark_done.callback(cog, mock_interaction, 999)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "not found" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_mark_done_no_guild(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test marking task done outside of a server.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        mock_interaction.guild = None

        await cog.mark_done.callback(cog, mock_interaction, 1)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "only be used in a server" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_mark_done_storage_fails(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test when storage mark_done fails.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        task = create_task(id=1)
        mock_storage.get_task_by_id.return_value = task
        mock_storage.mark_task_done.return_value = False

        await cog.mark_done.callback(cog, mock_interaction, 1)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "not found" in call_args[0][0]


class TestDeleteTaskCommand:
    """Tests for /delete command."""

    @pytest.mark.asyncio
    async def test_delete_task_success(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test successfully deleting a task.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        task = create_task(id=1)
        mock_storage.get_task_by_id.return_value = task
        mock_storage.delete_task.return_value = True

        await cog.delete_task.callback(cog, mock_interaction, 1)

        mock_storage.delete_task.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "deleted" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_delete_task_not_found(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test deleting non-existent task.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        mock_storage.get_task_by_id.return_value = None

        await cog.delete_task.callback(cog, mock_interaction, 999)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "not found" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_delete_task_no_guild(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test deleting task outside of a server.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        mock_interaction.guild = None

        await cog.delete_task.callback(cog, mock_interaction, 1)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "only be used in a server" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_delete_task_storage_fails(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test when storage delete fails.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        task = create_task(id=1)
        mock_storage.get_task_by_id.return_value = task
        mock_storage.delete_task.return_value = False

        await cog.delete_task.callback(cog, mock_interaction, 1)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "not found" in call_args[0][0]


class TestClearTasksCommand:
    """Tests for /clear command."""

    @pytest.mark.asyncio
    async def test_clear_tasks_success(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test successfully clearing completed tasks.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        mock_storage.clear_completed_tasks.return_value = 3

        await cog.clear_tasks.callback(cog, mock_interaction)

        mock_storage.clear_completed_tasks.assert_called_once()
        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Cleared 3" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True  # Success should be ephemeral

    @pytest.mark.asyncio
    async def test_clear_tasks_none(
        self, cog: TasksCog, mock_storage: MagicMock, mock_interaction: MagicMock
    ) -> None:
        """Test clearing when no tasks are completed.

        Args:
            cog: The TasksCog instance under test.
            mock_storage: The mock storage backend.
            mock_interaction: The mock Discord interaction.
        """
        mock_storage.clear_completed_tasks.return_value = 0

        await cog.clear_tasks.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "No completed tasks" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True  # Should be ephemeral

    @pytest.mark.asyncio
    async def test_clear_tasks_no_guild(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test clearing tasks outside of a server.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        mock_interaction.guild = None

        await cog.clear_tasks.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "only be used in a server" in call_args[0][0]


class TestCogErrorHandling:
    """Tests for cog error handling."""

    @pytest.mark.asyncio
    async def test_cooldown_error(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test cooldown error handling.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        from discord import app_commands

        error = app_commands.CommandOnCooldown(cooldown=MagicMock(), retry_after=5.0)

        await cog.cog_app_command_error(mock_interaction, error)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "Slow down" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_generic_error(
        self, cog: TasksCog, mock_interaction: MagicMock
    ) -> None:
        """Test generic error handling.

        Args:
            cog: The TasksCog instance under test.
            mock_interaction: The mock Discord interaction.
        """
        from discord import app_commands

        error = app_commands.AppCommandError("Test error")

        await cog.cog_app_command_error(mock_interaction, error)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        assert "error occurred" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True


class TestSetup:
    """Tests for cog setup function."""

    @pytest.mark.asyncio
    async def test_setup(self, mock_bot: MagicMock, mock_storage: MagicMock) -> None:
        """Test setup function adds cog to bot.

        Args:
            mock_bot: The mock Discord bot instance.
            mock_storage: The mock storage backend.
        """
        from todo_bot.cogs.tasks import setup

        mock_bot.add_cog = AsyncMock()

        await setup(mock_bot, mock_storage)

        mock_bot.add_cog.assert_called_once()
