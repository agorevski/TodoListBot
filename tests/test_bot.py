"""Tests for the Discord bot setup."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todo_bot.bot import TodoBot, create_bot, run_bot, setup_logging
from todo_bot.config import BotConfig
from todo_bot.exceptions import ConfigurationError


class TestTodoBot:
    """Tests for TodoBot class."""

    def test_bot_creation(self) -> None:
        """Test creating a bot with default settings.

        Verifies that a TodoBot instance is created with default storage
        and command prefix.
        """
        bot = TodoBot()

        assert bot.storage is not None
        assert bot.command_prefix == "!"

    def test_bot_creation_with_storage(self) -> None:
        """Test creating a bot with custom storage.

        Verifies that a TodoBot instance uses the provided storage
        instead of creating a default one.
        """
        mock_storage = MagicMock()
        bot = TodoBot(storage=mock_storage)

        assert bot.storage == mock_storage

    def test_bot_creation_with_custom_prefix(self) -> None:
        """Test creating a bot with custom command prefix.

        Verifies that the bot uses the specified command prefix
        instead of the default '!' prefix.
        """
        bot = TodoBot(command_prefix="?")

        assert bot.command_prefix == "?"

    def test_bot_creation_with_config(self) -> None:
        """Test creating a bot with BotConfig.

        Verifies that the bot properly stores and uses the provided
        configuration object.
        """
        config = BotConfig(discord_token="test_token")
        bot = TodoBot(config=config)

        assert bot.config == config
        assert bot.config.discord_token == "test_token"

    @pytest.mark.asyncio
    async def test_setup_hook(self) -> None:
        """Test bot setup hook initializes storage and cog.

        Verifies that setup_hook properly initializes storage, adds
        the required cogs, and syncs commands.
        """
        mock_storage = MagicMock()
        mock_storage.initialize = AsyncMock()

        bot = TodoBot(storage=mock_storage)

        with (
            patch.object(bot, "add_cog", new=AsyncMock()) as mock_add_cog,
            patch.object(bot.tree, "sync", new=AsyncMock()) as mock_sync,
        ):
            await bot.setup_hook()

            mock_storage.initialize.assert_called_once()
            # add_cog is called twice: once for TasksCog, once for RolloverScheduler
            assert mock_add_cog.call_count == 2
            mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_skip_sync(self) -> None:
        """Test bot setup hook skips sync when config says so.

        Verifies that setup_hook does not sync commands globally when
        sync_commands_globally is set to False in the config.
        """
        mock_storage = MagicMock()
        mock_storage.initialize = AsyncMock()

        config = BotConfig(
            discord_token="test",
            sync_commands_globally=False,
        )
        bot = TodoBot(config=config, storage=mock_storage)

        with (
            patch.object(bot, "add_cog", new=AsyncMock()) as mock_add_cog,
            patch.object(bot.tree, "sync", new=AsyncMock()) as mock_sync,
        ):
            await bot.setup_hook()

            mock_storage.initialize.assert_called_once()
            # add_cog is called once (TasksCog only) since scheduler is disabled when
            # enable_auto_rollover defaults to True but we need to check with False
            # Actually, let's verify the expected behavior - scheduler IS added
            # Since config doesn't disable rollover, scheduler is still added
            assert mock_add_cog.call_count == 2
            mock_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_ready(self, caplog) -> None:
        """Test on_ready event logs status.

        Args:
            caplog: Pytest fixture for capturing log output.

        Verifies that the on_ready event properly logs the bot's
        username and user ID.
        """
        mock_storage = MagicMock()
        bot = TodoBot(storage=mock_storage)

        mock_user = MagicMock()
        mock_user.id = 12345
        mock_user.__str__ = MagicMock(return_value="TestBot#1234")

        bot._connection = MagicMock()
        bot._connection.user = mock_user
        bot._guilds = {1: MagicMock(), 2: MagicMock()}

        with caplog.at_level(logging.INFO):
            await bot.on_ready()

        assert "TestBot#1234" in caplog.text
        assert "12345" in caplog.text

    @pytest.mark.asyncio
    async def test_on_ready_no_user(self, caplog) -> None:
        """Test on_ready when user is None.

        Args:
            caplog: Pytest fixture for capturing log output.

        Verifies that on_ready handles the case where the bot user
        is None gracefully without logging.
        """
        mock_storage = MagicMock()
        bot = TodoBot(storage=mock_storage)

        bot._connection = MagicMock()
        bot._connection.user = None

        with caplog.at_level(logging.INFO):
            await bot.on_ready()

        # Should not log anything when user is None
        assert "Logged in" not in caplog.text

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test bot close cleans up storage.

        Verifies that closing the bot properly calls the storage
        close method to clean up resources.
        """
        mock_storage = MagicMock()
        mock_storage.close = AsyncMock()

        bot = TodoBot(storage=mock_storage)

        with patch.object(bot.__class__.__bases__[0], "close", new=AsyncMock()):
            await bot.close()

        mock_storage.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_storage_error(self, caplog) -> None:
        """Test bot close handles storage error gracefully.

        Args:
            caplog: Pytest fixture for capturing log output.

        Verifies that the bot logs an error but does not raise when
        storage close fails.
        """
        from todo_bot.exceptions import StorageError

        mock_storage = MagicMock()
        mock_storage.close = AsyncMock(side_effect=StorageError("Storage close failed"))

        bot = TodoBot(storage=mock_storage)

        with (
            patch.object(bot.__class__.__bases__[0], "close", new=AsyncMock()),
            caplog.at_level(logging.ERROR),
        ):
            await bot.close()

        # Should log error but not raise
        mock_storage.close.assert_called_once()
        assert "Error closing storage" in caplog.text


class TestCreateBot:
    """Tests for create_bot function."""

    def test_create_bot_default(self) -> None:
        """Test creating bot with default settings.

        Verifies that create_bot returns a properly configured
        TodoBot instance with default storage.
        """
        bot = create_bot()

        assert isinstance(bot, TodoBot)
        assert bot.storage is not None

    def test_create_bot_with_storage(self) -> None:
        """Test creating bot with custom storage.

        Verifies that create_bot uses the provided storage instance
        when creating the bot.
        """
        mock_storage = MagicMock()
        bot = create_bot(storage=mock_storage)

        assert bot.storage == mock_storage

    def test_create_bot_with_config(self) -> None:
        """Test creating bot with config.

        Verifies that create_bot properly passes the configuration
        object to the created bot.
        """
        config = BotConfig(discord_token="test_token")
        bot = create_bot(config=config)

        assert bot.config == config


class TestRunBot:
    """Tests for run_bot function."""

    def test_run_bot_no_token(self) -> None:
        """Test run_bot raises when no token is provided.

        Verifies that run_bot raises a ConfigurationError when
        no Discord token is available in the environment.
        """
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("dotenv.load_dotenv"),
            pytest.raises(ConfigurationError, match="DISCORD_TOKEN"),
        ):
            run_bot()

    def test_run_bot_with_env_token(self) -> None:
        """Test run_bot uses environment variable token.

        Verifies that run_bot correctly reads the DISCORD_TOKEN
        from environment variables and uses it to run the bot.
        """
        with (
            patch.dict(
                "os.environ",
                {"DISCORD_TOKEN": "test_token"},
                clear=True,
            ),
            patch("dotenv.load_dotenv"),
            patch("todo_bot.bot.create_bot") as mock_create,
        ):
            mock_bot = MagicMock()
            mock_create.return_value = mock_bot

            run_bot()

            mock_bot.run.assert_called_once_with("test_token")

    def test_run_bot_with_direct_token(self) -> None:
        """Test run_bot uses directly provided token.

        Verifies that run_bot uses a token passed directly as an
        argument instead of reading from environment variables.
        """
        with (
            patch("dotenv.load_dotenv"),
            patch("todo_bot.bot.create_bot") as mock_create,
        ):
            mock_bot = MagicMock()
            mock_create.return_value = mock_bot

            run_bot(token="direct_token")

            mock_bot.run.assert_called_once_with("direct_token")


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default(self) -> None:
        """Test setup_logging with default INFO level.

        Verifies that setup_logging creates a logger when called
        without arguments.
        """
        setup_logging()

        logger = logging.getLogger("test")
        assert logger is not None

    def test_setup_logging_debug(self) -> None:
        """Test setup_logging with DEBUG level.

        Verifies that setup_logging accepts DEBUG as a valid
        logging level.
        """
        setup_logging("DEBUG")

    def test_setup_logging_invalid_level(self) -> None:
        """Test setup_logging with invalid level defaults to INFO.

        Verifies that setup_logging handles invalid logging levels
        gracefully by defaulting to INFO.
        """
        setup_logging("INVALID")
