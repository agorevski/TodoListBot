"""Main entry point for the Discord A/B/C Todo Bot."""

import logging
import signal
import sys
import types
from typing import Optional

from .bot import run_bot

logger = logging.getLogger(__name__)


class ShutdownHandler:
    """Handles graceful shutdown signals without global mutable state."""

    def __init__(self) -> None:
        """Initialize the shutdown handler."""
        self._shutdown_requested = False

    def handle_signal(
        self,
        sig: int,
        frame: Optional[types.FrameType],
    ) -> None:
        """Handle shutdown signals gracefully.

        Args:
            sig: Signal number
            frame: Current stack frame (unused)
        """
        if self._shutdown_requested:
            logger.warning("Forced shutdown requested")
            sys.exit(1)

        self._shutdown_requested = True
        signal_name = signal.Signals(sig).name
        logger.info("Received %s, initiating graceful shutdown...", signal_name)

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested


def setup_signal_handlers(handler: Optional[ShutdownHandler] = None) -> ShutdownHandler:
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


def main() -> None:
    """Run the Discord A/B/C Todo Bot."""
    setup_signal_handlers()
    run_bot()


if __name__ == "__main__":  # pragma: no cover
    main()
