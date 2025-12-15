"""Tests for the config module."""

import os
from unittest.mock import patch

import pytest

from todo_bot.config import (
    BUTTONS_PER_ROW,
    CONNECTION_RETRY_DELAY_SECONDS,
    DEFAULT_DB_PATH,
    DEFAULT_RETENTION_DAYS,
    MAX_BUTTONS_PER_VIEW,
    MAX_CONNECTION_RETRIES,
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    RATE_LIMIT_COMMANDS,
    RATE_LIMIT_SECONDS,
    SCHEMA_VERSION,
    VIEW_TIMEOUT_SECONDS,
    BotConfig,
)


class TestConstants:
    """Tests for config constants."""

    def test_description_length_constants(self):
        """Test description length constants are set correctly."""
        assert MAX_DESCRIPTION_LENGTH == 500
        assert MIN_DESCRIPTION_LENGTH == 1

    def test_rate_limit_constants(self):
        """Test rate limit constants are set correctly."""
        assert RATE_LIMIT_COMMANDS == 5
        assert RATE_LIMIT_SECONDS == 10.0

    def test_view_constants(self):
        """Test view constants are set correctly."""
        assert VIEW_TIMEOUT_SECONDS == 300.0
        assert MAX_BUTTONS_PER_VIEW == 25
        assert BUTTONS_PER_ROW == 5

    def test_database_constants(self):
        """Test database constants are set correctly."""
        assert DEFAULT_DB_PATH == "data/tasks.db"
        assert SCHEMA_VERSION == 2

    def test_connection_constants(self):
        """Test connection retry constants are set correctly."""
        assert MAX_CONNECTION_RETRIES == 3
        assert CONNECTION_RETRY_DELAY_SECONDS == 1.0

    def test_retention_constants(self):
        """Test retention constants are set correctly."""
        assert DEFAULT_RETENTION_DAYS == 0


class TestBotConfig:
    """Tests for BotConfig dataclass."""

    def test_bot_config_creation(self):
        """Test BotConfig creation with required fields."""
        config = BotConfig(discord_token="test_token")

        assert config.discord_token == "test_token"
        assert config.database_path == DEFAULT_DB_PATH
        assert config.log_level == "INFO"
        assert config.sync_commands_globally is True
        assert config.retention_days == 0

    def test_bot_config_custom_values(self):
        """Test BotConfig creation with custom values."""
        config = BotConfig(
            discord_token="my_token",
            database_path="custom/path.db",
            log_level="DEBUG",
            sync_commands_globally=False,
            retention_days=30,
        )

        assert config.discord_token == "my_token"
        assert config.database_path == "custom/path.db"
        assert config.log_level == "DEBUG"
        assert config.sync_commands_globally is False
        assert config.retention_days == 30

    def test_bot_config_is_frozen(self):
        """Test BotConfig is immutable (frozen)."""
        config = BotConfig(discord_token="test")

        with pytest.raises(AttributeError):
            config.discord_token = "changed"

    def test_bot_config_from_env(self):
        """Test BotConfig.from_env() loads from environment."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "env_token",
                "DATABASE_PATH": "env/db.db",
                "LOG_LEVEL": "DEBUG",
                "SYNC_COMMANDS_GLOBALLY": "false",
                "RETENTION_DAYS": "60",
            },
        ):
            config = BotConfig.from_env()

            assert config.discord_token == "env_token"
            assert config.database_path == "env/db.db"
            assert config.log_level == "DEBUG"
            assert config.sync_commands_globally is False
            assert config.retention_days == 60

    def test_bot_config_from_env_defaults(self):
        """Test BotConfig.from_env() uses defaults for missing values."""
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "token",
            },
            clear=True,
        ):
            config = BotConfig.from_env()

            assert config.discord_token == "token"
            assert config.database_path == DEFAULT_DB_PATH
            assert config.log_level == "INFO"
            assert config.sync_commands_globally is True
            assert config.retention_days == 0

    def test_bot_config_from_env_no_token_raises(self):
        """Test BotConfig.from_env() raises when DISCORD_TOKEN is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                BotConfig.from_env()

            assert "No Discord token provided" in str(exc_info.value)
