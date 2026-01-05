"""Extended tests for cog commands covering new features."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from todo_bot.cogs.tasks import TasksCog
from todo_bot.exceptions import StorageError
from todo_bot.models.task import Priority, Task

# Test constants
SERVER_ID = 123
CHANNEL_ID = 456
USER_ID = 789


def create_mock_interaction(guild: bool = True):
    """Create a mock Discord interaction.

    Args:
        guild: Whether the interaction is in a guild context. Defaults to True.

    Returns:
        A MagicMock configured to simulate a Discord interaction.
    """
    interaction = MagicMock()
    if guild:
        interaction.guild = MagicMock()
        interaction.guild.id = SERVER_ID
    else:
        interaction.guild = None
    interaction.channel_id = CHANNEL_ID
    interaction.user = MagicMock()
    interaction.user.id = USER_ID
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.original_response = AsyncMock()
    return interaction


def create_sample_task(id: int = 1):
    """Create a sample task for testing.

    Args:
        id: The task ID to assign. Defaults to 1.

    Returns:
        A Task instance with test data.
    """
    return Task(
        id=id,
        description="Test task",
        priority=Priority.A,
        server_id=SERVER_ID,
        channel_id=CHANNEL_ID,
        user_id=USER_ID,
    )


class TestGetUptime:
    """Tests for TasksCog.get_uptime instance method."""

    def test_get_uptime_returns_float(self):
        """Test get_uptime returns a float.

        Verifies that the get_uptime method returns a floating point number
        representing the elapsed time since the cog was initialized.
        """
        mock_bot = MagicMock()
        mock_storage = MagicMock()
        cog = TasksCog(mock_bot, mock_storage)
        uptime = cog.get_uptime()
        assert isinstance(uptime, float)

    def test_reset_start_time(self):
        """Test reset_start_time resets the timer.

        Verifies that calling reset_start_time sets the uptime back to
        approximately zero.
        """
        mock_bot = MagicMock()
        mock_storage = MagicMock()
        cog = TasksCog(mock_bot, mock_storage)
        cog.reset_start_time()
        uptime = cog.get_uptime()
        assert uptime >= 0.0  # May be slightly > 0 due to execution time
        assert uptime < 1.0  # Should be very small


class TestEditTaskCommand:
    """Tests for the /edit command."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot.

        Returns:
            A MagicMock configured as a Discord bot with empty guilds list.
        """
        bot = MagicMock()
        bot.guilds = []
        bot.latency = 0.05
        return bot

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage.

        Returns:
            A MagicMock configured as a storage backend with async methods.
        """
        storage = MagicMock()
        storage.get_task_by_id = AsyncMock()
        storage.update_task = AsyncMock(return_value=True)
        storage.get_stats = AsyncMock(
            return_value={
                "total_tasks": 10,
                "unique_users": 5,
                "schema_version": 1,
            }
        )
        return storage

    @pytest.fixture
    def cog(self, mock_bot, mock_storage):
        """Create a TasksCog instance.

        Args:
            mock_bot: The mock bot fixture.
            mock_storage: The mock storage fixture.

        Returns:
            A TasksCog instance configured with mock dependencies.
        """
        return TasksCog(mock_bot, mock_storage)

    @pytest.mark.asyncio
    async def test_edit_task_description(self, cog, mock_storage):
        """Test editing task description.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_task_by_id.return_value = create_sample_task()

        await cog.edit_task.callback(cog, interaction, task_id=1, description="Updated")

        mock_storage.update_task.assert_called_once()
        interaction.response.send_message.assert_called_once()
        assert "updated" in interaction.response.send_message.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_task_priority(self, cog, mock_storage):
        """Test editing task priority.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_task_by_id.return_value = create_sample_task()

        await cog.edit_task.callback(cog, interaction, task_id=1, priority="B")

        mock_storage.update_task.assert_called_once()
        call_kwargs = mock_storage.update_task.call_args[1]
        assert call_kwargs["priority"] == Priority.B

    @pytest.mark.asyncio
    async def test_edit_task_both(self, cog, mock_storage):
        """Test editing both description and priority.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_task_by_id.return_value = create_sample_task()

        await cog.edit_task.callback(
            cog,
            interaction,
            task_id=1,
            description="New desc",
            priority="C",
        )

        mock_storage.update_task.assert_called_once()
        call_kwargs = mock_storage.update_task.call_args[1]
        assert call_kwargs["description"] == "New desc"
        assert call_kwargs["priority"] == Priority.C

    @pytest.mark.asyncio
    async def test_edit_task_no_changes(self, cog, mock_storage):  # noqa: ARG002
        """Test edit with no changes shows error.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture (unused).
        """
        interaction = create_mock_interaction()

        await cog.edit_task.callback(cog, interaction, task_id=1)

        interaction.response.send_message.assert_called_once()
        assert "provide" in interaction.response.send_message.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_task_not_found(self, cog, mock_storage):
        """Test edit non-existent task.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_task_by_id.return_value = None

        await cog.edit_task.callback(cog, interaction, task_id=999, description="Test")

        interaction.response.send_message.assert_called_once()
        assert "not found" in interaction.response.send_message.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_task_no_guild(self, cog, mock_storage):  # noqa: ARG002
        """Test edit in DM fails.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture (unused).
        """
        interaction = create_mock_interaction(guild=False)

        await cog.edit_task.callback(cog, interaction, task_id=1, description="Test")

        interaction.response.send_message.assert_called_once()
        assert "server" in interaction.response.send_message.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_task_description_too_long(
        self,
        cog,
        mock_storage,  # noqa: ARG002
    ):
        """Test edit with too long description.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture (unused).
        """
        interaction = create_mock_interaction()
        long_desc = "x" * 600

        await cog.edit_task.callback(cog, interaction, task_id=1, description=long_desc)

        interaction.response.send_message.assert_called_once()
        assert "too long" in interaction.response.send_message.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_task_invalid_priority(self, cog, mock_storage):
        """Test edit with invalid priority.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_task_by_id.return_value = create_sample_task()

        await cog.edit_task.callback(cog, interaction, task_id=1, priority="Z")

        interaction.response.send_message.assert_called_once()
        # Priority.from_string should raise ValueError
        assert "invalid" in interaction.response.send_message.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_edit_task_storage_fails(self, cog, mock_storage):
        """Test edit when storage fails.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_task_by_id.return_value = create_sample_task()
        mock_storage.update_task.return_value = False

        await cog.edit_task.callback(cog, interaction, task_id=1, description="Test")

        interaction.response.send_message.assert_called_once()
        assert "not found" in interaction.response.send_message.call_args[0][0].lower()


class TestStatusCommand:
    """Tests for the /status command."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot.

        Returns:
            A MagicMock configured as a Discord bot with two guilds.
        """
        bot = MagicMock()
        bot.guilds = [MagicMock(), MagicMock()]
        bot.latency = 0.05
        return bot

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage.

        Returns:
            A MagicMock configured as a storage backend with stats.
        """
        storage = MagicMock()
        storage.get_stats = AsyncMock(
            return_value={
                "total_tasks": 100,
                "unique_users": 10,
                "schema_version": 1,
                "database_path": "test.db",
            }
        )
        return storage

    @pytest.fixture
    def cog(self, mock_bot, mock_storage):
        """Create a TasksCog instance.

        Args:
            mock_bot: The mock bot fixture.
            mock_storage: The mock storage fixture.

        Returns:
            A TasksCog instance configured with mock dependencies.
        """
        return TasksCog(mock_bot, mock_storage)

    @pytest.mark.asyncio
    async def test_status_command(self, cog, mock_storage):  # noqa: ARG002
        """Test status command returns embed.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture (unused).
        """
        interaction = create_mock_interaction()

        await cog.status.callback(cog, interaction)

        interaction.response.send_message.assert_called_once()
        call_kwargs = interaction.response.send_message.call_args[1]
        assert "embed" in call_kwargs

    @pytest.mark.asyncio
    async def test_status_shows_stats(self, cog, mock_storage):
        """Test status shows database stats.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()

        await cog.status.callback(cog, interaction)

        mock_storage.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_handles_stats_error(self, cog, mock_storage):
        """Test status handles storage error gracefully.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_stats.side_effect = StorageError("DB error")

        await cog.status.callback(cog, interaction)

        # Should still respond, just with error indicator
        interaction.response.send_message.assert_called_once()


class TestRolloverCommand:
    """Tests for the /rollover command."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot.

        Returns:
            A MagicMock configured as a Discord bot with empty guilds list.
        """
        bot = MagicMock()
        bot.guilds = []
        bot.latency = 0.05
        return bot

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage.

        Returns:
            A MagicMock configured as a storage backend with rollover methods.
        """
        storage = MagicMock()
        storage.get_tasks = AsyncMock(return_value=[])
        storage.rollover_incomplete_tasks = AsyncMock(return_value=0)
        return storage

    @pytest.fixture
    def cog(self, mock_bot, mock_storage):
        """Create a TasksCog instance.

        Args:
            mock_bot: The mock bot fixture.
            mock_storage: The mock storage fixture.

        Returns:
            A TasksCog instance configured with mock dependencies.
        """
        return TasksCog(mock_bot, mock_storage)

    @pytest.mark.asyncio
    async def test_rollover_no_incomplete_tasks(self, cog, mock_storage):
        """Test rollover when no incomplete tasks from yesterday.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        mock_storage.get_tasks.return_value = []

        await cog.rollover_tasks.callback(cog, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "No incomplete tasks" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_rollover_success(self, cog, mock_storage):
        """Test successful rollover of tasks.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        incomplete_task = create_sample_task()
        mock_storage.get_tasks.return_value = [incomplete_task]
        mock_storage.rollover_incomplete_tasks.return_value = 1

        await cog.rollover_tasks.callback(cog, interaction)

        mock_storage.rollover_incomplete_tasks.assert_called_once()
        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "Rolled over" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True  # Success should be ephemeral

    @pytest.mark.asyncio
    async def test_rollover_already_rolled(self, cog, mock_storage):
        """Test rollover when tasks already rolled over.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture.
        """
        interaction = create_mock_interaction()
        incomplete_task = create_sample_task()
        mock_storage.get_tasks.return_value = [incomplete_task]
        mock_storage.rollover_incomplete_tasks.return_value = 0  # Already rolled

        await cog.rollover_tasks.callback(cog, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "already rolled over" in call_args[0][0]
        assert call_args[1]["ephemeral"] is True

    @pytest.mark.asyncio
    async def test_rollover_no_guild(self, cog, mock_storage):  # noqa: ARG002
        """Test rollover in DM fails.

        Args:
            cog: The TasksCog fixture.
            mock_storage: The mock storage fixture (unused).
        """
        interaction = create_mock_interaction(guild=False)

        await cog.rollover_tasks.callback(cog, interaction)

        interaction.response.send_message.assert_called_once()
        call_args = interaction.response.send_message.call_args
        assert "server" in call_args[0][0].lower()
        assert call_args[1]["ephemeral"] is True
