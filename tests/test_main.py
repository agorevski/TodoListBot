"""Tests for the main entry point module."""

import signal
from unittest.mock import patch

import pytest

from todo_bot.main import (
    CleanupManager,
    ShutdownHandler,
    get_cleanup_manager,
    main,
    register_cleanup,
    reset_cleanup_manager,
    setup_signal_handlers,
)


class TestShutdownHandler:
    """Tests for ShutdownHandler class."""

    def test_shutdown_handler_init(self) -> None:
        """Test ShutdownHandler initializes with shutdown_requested = False.

        Verifies that a new ShutdownHandler instance has the shutdown_requested
        attribute set to False by default.
        """
        handler = ShutdownHandler()
        assert handler.shutdown_requested is False

    def test_shutdown_handler_first_call(self) -> None:
        """Test signal handler on first call sets shutdown flag.

        Verifies that calling handle_signal for the first time sets
        the shutdown_requested flag to True without exiting.
        """
        handler = ShutdownHandler()

        handler.handle_signal(signal.SIGINT, None)

        assert handler.shutdown_requested is True

    def test_shutdown_handler_second_call_exits(self) -> None:
        """Test signal handler on second call forces exit.

        Verifies that calling handle_signal a second time raises SystemExit
        with exit code 1, forcing immediate termination.

        Raises:
            SystemExit: Expected to be raised with code 1 on second signal.
        """
        handler = ShutdownHandler()
        handler.handle_signal(signal.SIGINT, None)  # First call

        with pytest.raises(SystemExit) as exc_info:
            handler.handle_signal(signal.SIGINT, None)  # Second call

        assert exc_info.value.code == 1


class TestSetupSignalHandlers:
    """Tests for setup_signal_handlers function."""

    def test_setup_signal_handlers_returns_handler(self) -> None:
        """Test signal handlers setup returns the handler.

        Verifies that setup_signal_handlers returns a ShutdownHandler instance
        and registers signal handlers via signal.signal.
        """
        with patch("signal.signal") as mock_signal:
            handler = setup_signal_handlers()

            assert isinstance(handler, ShutdownHandler)
            mock_signal.assert_called()

    def test_setup_signal_handlers_uses_provided_handler(self) -> None:
        """Test signal handlers setup uses provided handler.

        Verifies that when a custom ShutdownHandler is provided,
        setup_signal_handlers uses it instead of creating a new one.
        """
        custom_handler = ShutdownHandler()

        with patch("signal.signal"):
            returned_handler = setup_signal_handlers(handler=custom_handler)

            assert returned_handler is custom_handler


class TestCleanupManager:
    """Tests for CleanupManager class."""

    def test_cleanup_manager_singleton(self) -> None:
        """Test get_cleanup_manager returns the same instance.

        Verifies that get_cleanup_manager implements the singleton pattern
        by returning the same CleanupManager instance on subsequent calls.
        """
        reset_cleanup_manager()
        instance1 = get_cleanup_manager()
        instance2 = get_cleanup_manager()
        assert instance1 is instance2
        reset_cleanup_manager()

    def test_cleanup_manager_reset(self) -> None:
        """Test reset_cleanup_manager creates new instance.

        Verifies that calling reset_cleanup_manager clears the singleton,
        causing get_cleanup_manager to return a new instance.
        """
        instance1 = get_cleanup_manager()
        reset_cleanup_manager()
        instance2 = get_cleanup_manager()
        assert instance1 is not instance2
        reset_cleanup_manager()

    def test_cleanup_manager_is_registered_property(self) -> None:
        """Test CleanupManager.is_registered property.

        Verifies that is_registered is False initially and becomes True
        after calling register on the CleanupManager.
        """
        reset_cleanup_manager()
        manager = get_cleanup_manager()
        assert manager.is_registered is False

        with patch("atexit.register"):
            manager.register()
            assert manager.is_registered is True

        reset_cleanup_manager()

    def test_cleanup_manager_direct_instantiation(self) -> None:
        """Test CleanupManager can be instantiated directly.

        Verifies that CleanupManager can be created without using the
        singleton getter, and that it initializes with is_registered as False.
        """
        manager = CleanupManager()
        assert manager.is_registered is False


class TestRegisterCleanup:
    """Tests for register_cleanup function."""

    def test_register_cleanup_registers_atexit(self) -> None:
        """Test register_cleanup registers atexit handler.

        Verifies that calling register_cleanup registers a cleanup function
        with the atexit module to handle graceful shutdown.
        """
        # Reset the singleton
        reset_cleanup_manager()

        with patch("atexit.register") as mock_register:
            register_cleanup()

            mock_register.assert_called_once()

        # Restore
        reset_cleanup_manager()

    def test_register_cleanup_only_once(self) -> None:
        """Test register_cleanup only registers once.

        Verifies that multiple calls to register_cleanup only register
        the atexit handler once, preventing duplicate cleanup execution.
        """
        # Reset and register once
        reset_cleanup_manager()

        with patch("atexit.register") as mock_register:
            register_cleanup()  # First call
            register_cleanup()  # Second call

            # Should only call register once
            mock_register.assert_called_once()

        # Restore
        reset_cleanup_manager()


class TestCleanupOnExit:
    """Tests for CleanupManager._cleanup_on_exit function."""

    def test_cleanup_on_exit_logs_message(self) -> None:
        """Test _cleanup_on_exit logs shutdown message.

        Verifies that the cleanup function logs an appropriate message
        containing either 'exiting' or 'cleanup' when called.
        """
        with patch("todo_bot.main.logger") as mock_logger:
            CleanupManager._cleanup_on_exit()

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "exiting" in call_args.lower() or "cleanup" in call_args.lower()


class TestMain:
    """Tests for main function."""

    def test_main_calls_run_bot(self) -> None:
        """Test main function calls run_bot.

        Verifies that the main entry point function sets up signal handlers,
        registers cleanup, and calls run_bot to start the application.
        """
        reset_cleanup_manager()
        with (
            patch("todo_bot.main.setup_signal_handlers"),
            patch("todo_bot.main.register_cleanup"),
            patch("todo_bot.main.run_bot") as mock_run_bot,
        ):
            main()

            mock_run_bot.assert_called_once()
        reset_cleanup_manager()
