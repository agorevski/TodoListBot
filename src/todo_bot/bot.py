"""Discord bot setup and configuration."""

import logging

import discord
from discord.ext import commands

from .cogs.tasks import TasksCog
from .config import DEFAULT_DB_PATH, BotConfig
from .scheduler import RolloverScheduler, setup_scheduler
from .storage.base import TaskStorage
from .storage.sqlite import SQLiteTaskStorage
from .views.registry import ViewRegistry

logger = logging.getLogger(__name__)


class TodoBot(commands.Bot):
    """Discord bot for managing tasks using the A/B/C priority system."""

    def __init__(
        self,
        config: BotConfig | None = None,
        storage: TaskStorage | None = None,
        command_prefix: str = "!",
        **kwargs,
    ) -> None:
        """Initialize the todo bot.

        Args:
            config: Optional bot configuration (defaults to loading from env)
            storage: Optional task storage backend (defaults to SQLite)
            command_prefix: Prefix for text commands (not used, but required)
            **kwargs: Additional arguments to pass to commands.Bot
        """
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            **kwargs,
        )

        # Store configuration
        self._config = config

        # Use provided storage or create SQLite with configured path
        if storage is None:
            db_path = config.database_path if config else DEFAULT_DB_PATH
            self.storage = SQLiteTaskStorage(db_path=db_path)
            logger.info("Using SQLite storage at: %s", db_path)
        else:
            self.storage = storage
            logger.info("Using custom storage backend")

        # Create the view registry for auto-refresh support
        self.registry = ViewRegistry()

        # Scheduler will be initialized in setup_hook if enabled
        self._scheduler: RolloverScheduler | None = None

    @property
    def config(self) -> BotConfig | None:
        """Get the bot configuration."""
        return self._config

    async def setup_hook(self) -> None:
        """Set up the bot after login but before connecting to Discord."""
        logger.info("Setting up bot...")

        # Initialize storage
        await self.storage.initialize()
        logger.info("Storage initialized")

        # Add the tasks cog with the registry
        await self.add_cog(TasksCog(self, self.storage, self.registry))
        logger.info("Tasks cog loaded with view registry")

        # Sync slash commands with Discord
        # Note: In production, consider guild-specific sync to avoid rate limits
        sync_globally = True
        if self._config:
            sync_globally = self._config.sync_commands_globally

        if sync_globally:
            await self.tree.sync()
            logger.info("Slash commands synced globally")
        else:
            logger.info("Skipping global command sync (sync_commands_globally=false)")

        # Set up the rollover scheduler if enabled
        enable_rollover = True
        if self._config:
            enable_rollover = self._config.enable_auto_rollover

        if enable_rollover:
            self._scheduler = await setup_scheduler(self, self.storage)
            logger.info("Rollover scheduler enabled")
        else:
            logger.info("Rollover scheduler disabled (enable_auto_rollover=false)")

    async def on_ready(self) -> None:
        """Handle the bot becoming ready."""
        if self.user:
            logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)
            logger.info("Connected to %d guild(s)", len(self.guilds))

    async def close(self) -> None:
        """Clean up resources when the bot shuts down."""
        logger.info("Shutting down bot...")
        try:
            await self.storage.close()
            logger.info("Storage closed")
        except Exception as e:
            logger.error("Error closing storage: %s", e)
        finally:
            await super().close()
            logger.info("Bot shutdown complete")


def create_bot(
    config: BotConfig | None = None,
    storage: TaskStorage | None = None,
) -> TodoBot:
    """Create and configure a new TodoBot instance.

    Args:
        config: Optional bot configuration
        storage: Optional task storage backend

    Returns:
        Configured TodoBot instance
    """
    return TodoBot(config=config, storage=storage)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the bot.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduce discord.py logging noise
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


def run_bot(token: str | None = None) -> None:
    """Run the bot with the given token.

    Args:
        token: Discord bot token. If not provided, reads from DISCORD_TOKEN
               environment variable.
    """
    from dotenv import load_dotenv

    load_dotenv()

    # Load configuration from environment
    try:
        config = BotConfig.from_env()
    except ValueError:
        if token is None:
            raise
        # If token provided directly, create minimal config
        config = BotConfig(discord_token=token)

    # Override token if provided directly
    if token:
        config = BotConfig(
            discord_token=token,
            database_path=config.database_path,
            log_level=config.log_level,
            sync_commands_globally=config.sync_commands_globally,
            retention_days=config.retention_days,
        )

    # Setup logging
    setup_logging(config.log_level)

    logger.info("Starting Discord A/B/C Todo Bot...")
    bot = create_bot(config=config)
    bot.run(config.discord_token)
