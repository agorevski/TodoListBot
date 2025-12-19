"""Main entry point for the Discord A/B/C Todo Bot."""

import atexit
import logging
import signal
import sys
import threading
import types

from .bot import run_bot

logger = logging.getLogger(__name__)


# Module-level lock for thread-safe singleton access
_cleanup_manager_lock = threading.Lock()
_cleanup_manager_instance: "CleanupManager | None" = None


class CleanupManager:
    """Manages cleanup registration.

    Note: Use get_cleanup_manager() to get the singleton instance.
    Direct instantiation is allowed but not recommended for production use.
    """

    def __init__(self) -> None:
        """Initialize the cleanup manager."""
        self._registered: bool = False

    def register(self) -> None:
        """Register atexit handler for final cleanup logging.

        This ensures that even if an unexpected exit occurs,
        we log that the bot is shutting down.
        """
        if not self._registered:
            atexit.register(self._cleanup_on_exit)
            self._registered = True
            logger.debug("Cleanup handler registered")

    @property
    def is_registered(self) -> bool:
        """Check if cleanup handler is registered."""
        return self._registered

    @staticmethod
    def _cleanup_on_exit() -> None:
        """Cleanup function called on normal exit.

        Note: The actual database cleanup is handled by TodoBot.close()
        which is called by discord.py's event loop shutdown.
        This function is a safety net for logging purposes.
        """
        logger.info("Bot process exiting. Cleanup completed.")


def get_cleanup_manager() -> CleanupManager:
    """Get the singleton CleanupManager instance (thread-safe).

    Uses module-level state with a lock for thread safety.
    This is the preferred pattern over class-level mutable state.

    Returns:
        The singleton CleanupManager instance.
    """
    global _cleanup_manager_instance
    with _cleanup_manager_lock:
        if _cleanup_manager_instance is None:
            _cleanup_manager_instance = CleanupManager()
        return _cleanup_manager_instance


def reset_cleanup_manager() -> None:
    """Reset the singleton CleanupManager (for testing).

    This allows tests to start with a fresh CleanupManager instance.
    """
    global _cleanup_manager_instance
    with _cleanup_manager_lock:
        _cleanup_manager_instance = None


class ShutdownHandler:
    """Handles graceful shutdown signals without global mutable state."""

    def __init__(self) -> None:
        """Initialize the shutdown handler."""
        self._shutdown_requested = False

    def handle_signal(
        self,
        sig: int,
        frame: types.FrameType | None,  # noqa: ARG002
    ) -> None:
        """Handle shutdown signals gracefully.

        Args:
            sig: Signal number
            frame: Current stack frame (required by signal handler signature)
        """
        if self._shutdown_requested:
            logger.warning("Forced shutdown requested")
            sys.exit(1)

        self._shutdown_requested = True
        signal_name = signal.Signals(sig).name
        logger.info("Received %s, initiating graceful shutdown...", signal_name)
        # Note: discord.py handles the actual shutdown when it receives
        # KeyboardInterrupt. The bot.close() method ensures storage.close()
        # is called properly.

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested


def setup_signal_handlers(
    handler: ShutdownHandler | None = None,
) -> ShutdownHandler:
    """Set up signal handlers for graceful shutdown.

    Args:
        handler: Optional ShutdownHandler instance to use

    Returns:
        The ShutdownHandler instance being used
    """
    if handler is None:
        handler = ShutdownHandler()

    # Handle SIGINT (Ctrl+C) and SIGTERM
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, handler.handle_signal)
    signal.signal(signal.SIGINT, handler.handle_signal)

    return handler


def register_cleanup() -> None:
    """Register atexit handler for final cleanup logging.

    This ensures that even if an unexpected exit occurs,
    we log that the bot is shutting down.
    """
    get_cleanup_manager().register()


def main() -> None:
    """Run the Discord A/B/C Todo Bot."""
    setup_signal_handlers()
    register_cleanup()
    run_bot()


if __name__ == "__main__":  # pragma: no cover
    main()
