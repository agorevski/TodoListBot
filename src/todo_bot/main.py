"""Main entry point for the Discord A/B/C Todo Bot."""

import atexit
import logging
import signal
import sys
import types

from .bot import run_bot

logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages cleanup registration without global mutable state."""

    _instance: "CleanupManager | None" = None
    _registered: bool = False

    @classmethod
    def get_instance(cls) -> "CleanupManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None
        cls._registered = False

    def register(self) -> None:
        """Register atexit handler for final cleanup logging.

        This ensures that even if an unexpected exit occurs,
        we log that the bot is shutting down.
        """
        if not CleanupManager._registered:
            atexit.register(self._cleanup_on_exit)
            CleanupManager._registered = True
            logger.debug("Cleanup handler registered")

    @staticmethod
    def _cleanup_on_exit() -> None:
        """Cleanup function called on normal exit.

        Note: The actual database cleanup is handled by TodoBot.close()
        which is called by discord.py's event loop shutdown.
        This function is a safety net for logging purposes.
        """
        logger.info("Bot process exiting. Cleanup completed.")


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
    CleanupManager.get_instance().register()


def main() -> None:
    """Run the Discord A/B/C Todo Bot."""
    setup_signal_handlers()
    register_cleanup()
    run_bot()


if __name__ == "__main__":  # pragma: no cover
    main()
