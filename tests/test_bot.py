"""Tests for the Discord bot setup."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todo_bot.bot import TodoBot, create_bot, run_bot, setup_logging
from todo_bot.config import BotConfig


class TestTodoBot:
    """Tests for TodoBot class."""

    def test_bot_creation(self) -> None:
        """Test creating a bot with default settings."""
        bot = TodoBot()

        assert bot.storage is not None
        assert bot.command_prefix == "!"

    def test_bot_creation_with_storage(self) -> None:
        """Test creating a bot with custom storage."""
        mock_storage = MagicMock()
        bot = TodoBot(storage=mock_storage)

        assert bot.storage == mock_storage

    def test_bot_creation_with_custom_prefix(self) -> None:
        """Test creating a bot with custom command prefix."""
        bot = TodoBot(command_prefix="?")

        assert bot.command_prefix == "?"

    def test_bot_creation_with_config(self) -> None:
        """Test creating a bot with BotConfig."""
        config = BotConfig(discord_token="test_token")
        bot = TodoBot(config=config)

        assert bot.config == config
        assert bot.config.discord_token == "test_token"

    @pytest.mark.asyncio
    async def test_setup_hook(self) -> None:
        """Test bot setup hook initializes storage and cog."""
        mock_storage = MagicMock()
        mock_storage.initialize = AsyncMock()

        bot = TodoBot(storage=mock_storage)

        with patch.object(bot, "add_cog", new=AsyncMock()) as mock_add_cog:
            with patch.object(bot.tree, "sync", new=AsyncMock()) as mock_sync:
                await bot.setup_hook()

                mock_storage.initialize.assert_called_once()
                mock_add_cog.assert_called_once()
                mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_hook_skip_sync(self) -> None:
        """Test bot setup hook skips sync when config says so."""
        mock_storage = MagicMock()
        mock_storage.initialize = AsyncMock()

        config = BotConfig(
            discord_token="test",
            sync_commands_globally=False,
        )
        bot = TodoBot(config=config, storage=mock_storage)

        with patch.object(bot, "add_cog", new=AsyncMock()) as mock_add_cog:
            with patch.object(bot.tree, "sync", new=AsyncMock()) as mock_sync:
                await bot.setup_hook()

                mock_storage.initialize.assert_called_once()
                mock_add_cog.assert_called_once()
                mock_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_ready(self, caplog) -> None:
        """Test on_ready event logs status."""
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
        """Test on_ready when user is None."""
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
        """Test bot close cleans up storage."""
        mock_storage = MagicMock()
        mock_storage.close = AsyncMock()

        bot = TodoBot(storage=mock_storage)

        with patch.object(bot.__class__.__bases__[0], "close", new=AsyncMock()):
            await bot.close()

        mock_storage.close.assert_called_once()


class TestCreateBot:
    """Tests for create_bot function."""

    def test_create_bot_default(self) -> None:
        """Test creating bot with default settings."""
        bot = create_bot()

        assert isinstance(bot, TodoBot)
        assert bot.storage is not None

    def test_create_bot_with_storage(self) -> None:
        """Test creating bot with custom storage."""
        mock_storage = MagicMock()
        bot = create_bot(storage=mock_storage)

        assert bot.storage == mock_storage

    def test_create_bot_with_config(self) -> None:
        """Test creating bot with config."""
        config = BotConfig(discord_token="test_token")
        bot = create_bot(config=config)

        assert bot.config == config


class TestRunBot:
    """Tests for run_bot function."""

    def test_run_bot_no_token(self) -> None:
        """Test run_bot raises when no token is provided."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("dotenv.load_dotenv"):
                with pytest.raises(ValueError, match="DISCORD_TOKEN"):
                    run_bot()

    def test_run_bot_with_env_token(self) -> None:
        """Test run_bot uses environment variable token."""
        with patch.dict(
            "os.environ",
            {"DISCORD_TOKEN": "test_token"},
            clear=True,
        ):
            with patch("dotenv.load_dotenv"):
                with patch(
                    "todo_bot.bot.create_bot"
                ) as mock_create:
                    mock_bot = MagicMock()
                    mock_create.return_value = mock_bot

                    run_bot()

                    mock_bot.run.assert_called_once_with("test_token")

    def test_run_bot_with_direct_token(self) -> None:
        """Test run_bot uses directly provided token."""
        with patch("dotenv.load_dotenv"):
            with patch("todo_bot.bot.create_bot") as mock_create:
                mock_bot = MagicMock()
                mock_create.return_value = mock_bot

                run_bot(token="direct_token")

                mock_bot.run.assert_called_once_with("direct_token")


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default(self) -> None:
        """Test setup_logging with default INFO level."""
        setup_logging()

        logger = logging.getLogger("test")
        assert logger is not None

    def test_setup_logging_debug(self) -> None:
        """Test setup_logging with DEBUG level."""
        setup_logging("DEBUG")

    def test_setup_logging_invalid_level(self) -> None:
        """Test setup_logging with invalid level defaults to INFO."""
        setup_logging("INVALID")
