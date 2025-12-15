"""Tests for the main entry point module."""

import signal
from unittest.mock import patch

import pytest

from todo_bot.main import (
    ShutdownHandler,
    main,
    setup_signal_handlers,
)


class TestShutdownHandler:
    """Tests for ShutdownHandler class."""

    def test_shutdown_handler_init(self) -> None:
        """Test ShutdownHandler initializes with shutdown_requested = False."""
        handler = ShutdownHandler()
        assert handler.shutdown_requested is False

    def test_shutdown_handler_first_call(self) -> None:
        """Test signal handler on first call sets shutdown flag."""
        handler = ShutdownHandler()

        handler.handle_signal(signal.SIGINT, None)

        assert handler.shutdown_requested is True

    def test_shutdown_handler_second_call_exits(self) -> None:
        """Test signal handler on second call forces exit."""
        handler = ShutdownHandler()
        handler.handle_signal(signal.SIGINT, None)  # First call

        with pytest.raises(SystemExit) as exc_info:
            handler.handle_signal(signal.SIGINT, None)  # Second call

        assert exc_info.value.code == 1


class TestSetupSignalHandlers:
    """Tests for setup_signal_handlers function."""

    def test_setup_signal_handlers_returns_handler(self) -> None:
        """Test signal handlers setup returns the handler."""
        with patch("signal.signal") as mock_signal:
            handler = setup_signal_handlers()

            assert isinstance(handler, ShutdownHandler)
            mock_signal.assert_called()

    def test_setup_signal_handlers_uses_provided_handler(self) -> None:
        """Test signal handlers setup uses provided handler."""
        custom_handler = ShutdownHandler()

        with patch("signal.signal"):
            returned_handler = setup_signal_handlers(handler=custom_handler)

            assert returned_handler is custom_handler


class TestMain:
    """Tests for main function."""

    def test_main_calls_run_bot(self) -> None:
        """Test main function calls run_bot."""
        with (
            patch("todo_bot.main.setup_signal_handlers"),
            patch("todo_bot.main.register_cleanup"),
            patch("todo_bot.main.run_bot") as mock_run_bot,
        ):
            main()

            mock_run_bot.assert_called_once()
