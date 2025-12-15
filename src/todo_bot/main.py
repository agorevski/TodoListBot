"""Main entry point for the Discord A/B/C Todo Bot."""

import atexit
import logging
import signal
import sys
import types

from .bot import run_bot

logger = logging.getLogger(__name__)

# Global reference for cleanup registration
_cleanup_registered = False


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
    global _cleanup_registered
    if not _cleanup_registered:
        atexit.register(_cleanup_on_exit)
        _cleanup_registered = True
        logger.debug("Cleanup handler registered")


def _cleanup_on_exit() -> None:
    """Cleanup function called on normal exit.

    Note: The actual database cleanup is handled by TodoBot.close()
    which is called by discord.py's event loop shutdown.
    This function is a safety net for logging purposes.
    """
    logger.info("Bot process exiting. Cleanup completed.")


def main() -> None:
    """Run the Discord A/B/C Todo Bot."""
    setup_signal_handlers()
    register_cleanup()
    run_bot()


if __name__ == "__main__":  # pragma: no cover
    main()
