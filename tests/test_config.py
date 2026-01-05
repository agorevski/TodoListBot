"""Tests for the config module."""

import os
from unittest.mock import patch

import pytest

from todo_bot.config import (
    BUTTONS_PER_ROW,
    CONNECTION_RETRY_DELAY_SECONDS,
    DEFAULT_DB_PATH,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_ROLLOVER_HOUR_UTC,
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
from todo_bot.exceptions import ConfigurationError


class TestConstants:
    """Tests for config constants."""

    def test_description_length_constants(self):
        """Test description length constants are set correctly.

        Verifies that MAX_DESCRIPTION_LENGTH and MIN_DESCRIPTION_LENGTH
        have the expected default values.
        """
        assert MAX_DESCRIPTION_LENGTH == 500
        assert MIN_DESCRIPTION_LENGTH == 1

    def test_rate_limit_constants(self):
        """Test rate limit constants are set correctly.

        Verifies that RATE_LIMIT_COMMANDS and RATE_LIMIT_SECONDS
        have the expected default values for rate limiting.
        """
        assert RATE_LIMIT_COMMANDS == 5
        assert RATE_LIMIT_SECONDS == 10.0

    def test_view_constants(self):
        """Test view constants are set correctly.

        Verifies that VIEW_TIMEOUT_SECONDS, MAX_BUTTONS_PER_VIEW, and
        BUTTONS_PER_ROW have the expected default values for Discord views.
        """
        assert VIEW_TIMEOUT_SECONDS == 300.0
        assert MAX_BUTTONS_PER_VIEW == 25
        assert BUTTONS_PER_ROW == 5

    def test_database_constants(self):
        """Test database constants are set correctly.

        Verifies that DEFAULT_DB_PATH and SCHEMA_VERSION have the
        expected default values for database configuration.
        """
        assert DEFAULT_DB_PATH == "data/tasks.db"
        assert SCHEMA_VERSION == 2

    def test_connection_constants(self):
        """Test connection retry constants are set correctly.

        Verifies that MAX_CONNECTION_RETRIES and CONNECTION_RETRY_DELAY_SECONDS
        have the expected default values for connection handling.
        """
        assert MAX_CONNECTION_RETRIES == 3
        assert CONNECTION_RETRY_DELAY_SECONDS == 1.0

    def test_retention_constants(self):
        """Test retention constants are set correctly.

        Verifies that DEFAULT_RETENTION_DAYS has the expected default
        value for task retention configuration.
        """
        assert DEFAULT_RETENTION_DAYS == 0

    def test_rollover_constants(self):
        """Test rollover constants are set correctly.

        Verifies that DEFAULT_ROLLOVER_HOUR_UTC has the expected default
        value for daily task rollover timing.
        """
        assert DEFAULT_ROLLOVER_HOUR_UTC == 0


class TestBotConfig:
    """Tests for BotConfig dataclass."""

    def test_bot_config_creation(self):
        """Test BotConfig creation with required fields.

        Verifies that a BotConfig instance can be created with only the
        required discord_token and that all other fields use defaults.
        """
        config = BotConfig(discord_token="test_token")

        assert config.discord_token == "test_token"
        assert config.database_path == DEFAULT_DB_PATH
        assert config.log_level == "INFO"
        assert config.sync_commands_globally is True
        assert config.retention_days == 0
        assert config.rollover_hour_utc == 0

    def test_bot_config_custom_values(self):
        """Test BotConfig creation with custom values.

        Verifies that a BotConfig instance correctly stores all custom
        values when provided during creation.
        """
        config = BotConfig(
            discord_token="my_token",
            database_path="custom/path.db",
            log_level="DEBUG",
            sync_commands_globally=False,
            retention_days=30,
            rollover_hour_utc=14,
        )

        assert config.discord_token == "my_token"
        assert config.database_path == "custom/path.db"
        assert config.log_level == "DEBUG"
        assert config.sync_commands_globally is False
        assert config.retention_days == 30
        assert config.rollover_hour_utc == 14

    def test_bot_config_is_frozen(self):
        """Test BotConfig is immutable (frozen).

        Verifies that BotConfig instances cannot be modified after creation,
        raising AttributeError when attempting to change attributes.
        """
        config = BotConfig(discord_token="test")

        with pytest.raises(AttributeError):
            config.discord_token = "changed"

    def test_bot_config_from_env(self):
        """Test BotConfig.from_env() loads from environment.

        Verifies that BotConfig.from_env() correctly reads and parses
        all configuration values from environment variables.
        """
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "env_token",
                "DATABASE_PATH": "env/db.db",
                "LOG_LEVEL": "DEBUG",
                "SYNC_COMMANDS_GLOBALLY": "false",
                "RETENTION_DAYS": "60",
                "ROLLOVER_HOUR_UTC": "14",
            },
        ):
            config = BotConfig.from_env()

            assert config.discord_token == "env_token"
            assert config.database_path == "env/db.db"
            assert config.log_level == "DEBUG"
            assert config.sync_commands_globally is False
            assert config.retention_days == 60
            assert config.rollover_hour_utc == 14

    def test_bot_config_from_env_defaults(self):
        """Test BotConfig.from_env() uses defaults for missing values.

        Verifies that BotConfig.from_env() applies default values for
        optional environment variables when they are not set.
        """
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
            assert config.rollover_hour_utc == 0

    def test_bot_config_from_env_no_token_raises(self):
        """Test BotConfig.from_env() raises when DISCORD_TOKEN is missing.

        Verifies that ConfigurationError is raised with an appropriate
        message when the required DISCORD_TOKEN environment variable is not set.
        """
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                BotConfig.from_env()

            assert "No Discord token provided" in str(exc_info.value)

    def test_bot_config_from_env_invalid_rollover_hour_raises(self):
        """Test BotConfig.from_env() raises when ROLLOVER_HOUR_UTC is invalid.

        Verifies that ConfigurationError is raised when ROLLOVER_HOUR_UTC
        is set to a value outside the valid range of 0-23.
        """
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "token",
                "ROLLOVER_HOUR_UTC": "25",
            },
            clear=True,
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                BotConfig.from_env()

            assert "must be between 0 and 23" in str(exc_info.value)

    def test_bot_config_from_env_non_integer_rollover_hour_raises(self):
        """Test BotConfig.from_env() raises when ROLLOVER_HOUR_UTC is not an integer.

        Verifies that ConfigurationError is raised when ROLLOVER_HOUR_UTC
        is set to a non-numeric string value that cannot be parsed.
        """
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "token",
                "ROLLOVER_HOUR_UTC": "noon",
            },
            clear=True,
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                BotConfig.from_env()

            assert "must be a valid integer" in str(exc_info.value)
