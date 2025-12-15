"""Tests for the main entry point module."""

import signal
from unittest.mock import patch

import pytest

from todo_bot.main import (
    ShutdownHandler,
    _cleanup_on_exit,
    main,
    register_cleanup,
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


class TestRegisterCleanup:
    """Tests for register_cleanup function."""

    def test_register_cleanup_registers_atexit(self) -> None:
        """Test register_cleanup registers atexit handler."""
        import todo_bot.main as main_module

        # Reset the global flag
        original_value = main_module._cleanup_registered
        main_module._cleanup_registered = False

        with patch("atexit.register") as mock_register:
            register_cleanup()

            mock_register.assert_called_once_with(_cleanup_on_exit)

        # Restore original value
        main_module._cleanup_registered = original_value

    def test_register_cleanup_only_once(self) -> None:
        """Test register_cleanup only registers once."""
        import todo_bot.main as main_module

        # Set the global flag to True (already registered)
        original_value = main_module._cleanup_registered
        main_module._cleanup_registered = True

        with patch("atexit.register") as mock_register:
            register_cleanup()

            # Should not call register since already registered
            mock_register.assert_not_called()

        # Restore original value
        main_module._cleanup_registered = original_value


class TestCleanupOnExit:
    """Tests for _cleanup_on_exit function."""

    def test_cleanup_on_exit_logs_message(self) -> None:
        """Test _cleanup_on_exit logs shutdown message."""
        with patch("todo_bot.main.logger") as mock_logger:
            _cleanup_on_exit()

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "exiting" in call_args.lower() or "cleanup" in call_args.lower()


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
